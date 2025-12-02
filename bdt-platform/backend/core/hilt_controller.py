"""
Human-in-the-Loop (HILT) Controller for L4 Agent oversight
"""
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import json
import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

from ..config import settings
from ..database import (
    get_db, DelegatedTask, TaskStatus, ApprovalAction,
    AuditLog, Persona
)
from .decision_engine import DecisionResult

logger = logging.getLogger(__name__)

class HILTMode(str, Enum):
    """HILT operation modes"""
    FULL_AUTO = "full_auto"          # No approval needed (L4 full autonomy)
    SELECTIVE = "selective"           # Approval for high-risk/low-confidence
    GUIDED = "guided"                 # All actions need approval (L3 mode)
    LEARNING = "learning"             # Approval with feedback collection

@dataclass
class ApprovalRequest:
    """Request for human approval"""
    task_id: str
    task_description: str
    decision: str
    confidence: float
    risk_score: float
    reasoning: List[str]
    suggested_actions: List[Dict]
    boundary_concerns: List[Dict]
    timeout: int  # seconds
    created_at: datetime

@dataclass
class ApprovalResponse:
    """Human approval response"""
    action: ApprovalAction
    modified_decision: Optional[str]
    feedback: Optional[str]
    delegate_to: Optional[str]
    approved_by: str
    response_time: float  # seconds

class HILTController:
    """
    Controller for Human-in-the-Loop interactions
    """
    
    def __init__(self):
        self.mode = HILTMode.SELECTIVE  # Default mode
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        self.approval_callbacks: Dict[str, asyncio.Future] = {}
        
        # Configuration
        self.confidence_threshold = settings.HILT_CONFIDENCE_THRESHOLD
        self.risk_threshold = settings.HILT_RISK_THRESHOLD
        self.auto_approve_low_risk = settings.HILT_AUTO_APPROVE_LOW_RISK
        self.approval_timeout = settings.HILT_APPROVAL_TIMEOUT
    
    async def request_approval(
        self,
        task: DelegatedTask,
        decision_result: DecisionResult,
        mode_override: Optional[HILTMode] = None
    ) -> ApprovalResponse:
        """
        Request human approval for a task execution
        """
        mode = mode_override or self.mode
        
        # Check if approval needed based on mode
        if not self._needs_approval(decision_result, mode):
            # Auto-approve
            return ApprovalResponse(
                action=ApprovalAction.APPROVE,
                modified_decision=None,
                feedback="Auto-approved based on HILT settings",
                delegate_to=None,
                approved_by="system",
                response_time=0
            )
        
        # Create approval request
        request = ApprovalRequest(
            task_id=str(task.id),
            task_description=task.task_description,
            decision=decision_result.decision,
            confidence=decision_result.confidence,
            risk_score=decision_result.risk_score,
            reasoning=decision_result.reasoning,
            suggested_actions=decision_result.suggested_actions,
            boundary_concerns=[
                {
                    "boundary": str(check.boundary_id),
                    "violated": check.violated,
                    "severity": check.severity,
                    "recommendation": check.recommendation
                }
                for check in decision_result.boundary_checks
                if check.violated or check.distance_to_boundary < 0.3
            ],
            timeout=self.approval_timeout,
            created_at=datetime.utcnow()
        )
        
        # Store request
        self.pending_approvals[str(task.id)] = request
        
        # Create future for async response
        future = asyncio.Future()
        self.approval_callbacks[str(task.id)] = future
        
        # Update task status
        with get_db() as db:
            task_db = db.query(DelegatedTask).filter(
                DelegatedTask.id == task.id
            ).first()
            if task_db:
                task_db.status = TaskStatus.AWAITING_APPROVAL
                task_db.requires_approval = True
                db.commit()
        
        # Notify UI (webhook/websocket)
        await self._notify_approval_required(request)
        
        # Wait for response with timeout
        try:
            response = await asyncio.wait_for(
                future,
                timeout=request.timeout
            )
            
            # Log approval
            self._log_approval(task, request, response)
            
            return response
            
        except asyncio.TimeoutError:
            # Timeout - apply default action
            logger.warning(f"Approval timeout for task {task.id}")
            
            if mode == HILTMode.LEARNING:
                # In learning mode, proceed but log
                return ApprovalResponse(
                    action=ApprovalAction.APPROVE,
                    modified_decision=None,
                    feedback="Timeout - proceeded in learning mode",
                    delegate_to=None,
                    approved_by="system-timeout",
                    response_time=request.timeout
                )
            else:
                # In other modes, reject on timeout
                return ApprovalResponse(
                    action=ApprovalAction.REJECT,
                    modified_decision=None,
                    feedback="Timeout - no response received",
                    delegate_to=None,
                    approved_by="system-timeout",
                    response_time=request.timeout
                )
    
    async def submit_approval(
        self,
        task_id: str,
        action: ApprovalAction,
        approved_by: str,
        modified_decision: Optional[str] = None,
        feedback: Optional[str] = None,
        delegate_to: Optional[str] = None
    ) -> bool:
        """
        Submit approval decision for a pending request
        """
        if task_id not in self.pending_approvals:
            logger.error(f"No pending approval for task {task_id}")
            return False
        
        request = self.pending_approvals[task_id]
        response_time = (datetime.utcnow() - request.created_at).total_seconds()
        
        response = ApprovalResponse(
            action=action,
            modified_decision=modified_decision,
            feedback=feedback,
            delegate_to=delegate_to,
            approved_by=approved_by,
            response_time=response_time
        )
        
        # Update task in database
        with get_db() as db:
            task = db.query(DelegatedTask).filter(
                DelegatedTask.id == task_id
            ).first()
            
            if task:
                task.approval_status = action
                task.approved_by = approved_by
                task.approved_at = datetime.utcnow()
                task.approval_notes = feedback
                
                if action == ApprovalAction.APPROVE:
                    task.status = TaskStatus.APPROVED
                    if modified_decision:
                        # Update task with modified decision
                        task.task_description = modified_decision
                elif action == ApprovalAction.REJECT:
                    task.status = TaskStatus.REJECTED
                elif action == ApprovalAction.DELEGATE:
                    task.status = TaskStatus.PENDING
                    # TODO: Handle delegation
                
                db.commit()
        
        # Resolve future if exists
        if task_id in self.approval_callbacks:
            future = self.approval_callbacks[task_id]
            if not future.done():
                future.set_result(response)
        
        # Clean up
        del self.pending_approvals[task_id]
        if task_id in self.approval_callbacks:
            del self.approval_callbacks[task_id]
        
        logger.info(f"Approval submitted for task {task_id}: {action.value}")
        return True
    
    def set_mode(self, mode: HILTMode, persona_id: Optional[str] = None):
        """
        Set HILT operation mode
        """
        if persona_id:
            # Set mode for specific persona
            with get_db() as db:
                persona = db.query(Persona).filter(
                    Persona.id == persona_id
                ).first()
                if persona:
                    if not persona.config:
                        persona.config = {}
                    persona.config["hilt_mode"] = mode.value
                    db.commit()
        else:
            # Set global mode
            self.mode = mode
        
        logger.info(f"HILT mode set to {mode.value}")
    
    def get_pending_approvals(
        self,
        persona_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of pending approval requests
        """
        pending = []
        
        for task_id, request in self.pending_approvals.items():
            # Filter by persona if specified
            if persona_id:
                with get_db() as db:
                    task = db.query(DelegatedTask).filter(
                        DelegatedTask.id == task_id
                    ).first()
                    if task and str(task.persona_id) != persona_id:
                        continue
            
            pending.append({
                "task_id": request.task_id,
                "task_description": request.task_description,
                "decision": request.decision,
                "confidence": request.confidence,
                "risk_score": request.risk_score,
                "reasoning": request.reasoning,
                "boundary_concerns": request.boundary_concerns,
                "created_at": request.created_at.isoformat(),
                "timeout_at": (
                    request.created_at + timedelta(seconds=request.timeout)
                ).isoformat()
            })
        
        return pending
    
    def get_approval_statistics(
        self,
        persona_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get approval statistics for a persona
        """
        try:
            with get_db() as db:
                since = datetime.utcnow() - timedelta(days=days)
                
                tasks = db.query(DelegatedTask).filter(
                    DelegatedTask.persona_id == persona_id,
                    DelegatedTask.created_at >= since
                ).all()
                
                stats = {
                    "total_tasks": len(tasks),
                    "required_approval": sum(
                        1 for t in tasks if t.requires_approval
                    ),
                    "approved": sum(
                        1 for t in tasks 
                        if t.approval_status == ApprovalAction.APPROVE
                    ),
                    "rejected": sum(
                        1 for t in tasks
                        if t.approval_status == ApprovalAction.REJECT
                    ),
                    "modified": sum(
                        1 for t in tasks
                        if t.approval_status == ApprovalAction.MODIFY
                    ),
                    "avg_response_time": None,
                    "approval_rate": 0,
                    "auto_approval_rate": 0
                }
                
                # Calculate average response time
                response_times = [
                    (t.approved_at - t.created_at).total_seconds()
                    for t in tasks
                    if t.approved_at and t.created_at
                ]
                
                if response_times:
                    stats["avg_response_time"] = sum(response_times) / len(response_times)
                
                # Calculate approval rate
                if stats["required_approval"] > 0:
                    stats["approval_rate"] = stats["approved"] / stats["required_approval"]
                
                # Calculate auto-approval rate
                auto_approved = sum(
                    1 for t in tasks
                    if t.approved_by == "system" and t.approval_status == ApprovalAction.APPROVE
                )
                
                if stats["total_tasks"] > 0:
                    stats["auto_approval_rate"] = auto_approved / stats["total_tasks"]
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get approval statistics: {str(e)}")
            return {}
    
    def _needs_approval(self, decision_result: DecisionResult, mode: HILTMode) -> bool:
        """
        Determine if approval is needed based on mode and decision
        """
        if mode == HILTMode.FULL_AUTO:
            return False
        
        if mode == HILTMode.GUIDED:
            return True
        
        if mode == HILTMode.LEARNING:
            # In learning mode, require approval but allow timeout override
            return True
        
        if mode == HILTMode.SELECTIVE:
            # Check if already flagged
            if decision_result.requires_approval:
                return True
            
            # Check confidence threshold
            if decision_result.confidence < self.confidence_threshold:
                return True
            
            # Check risk threshold
            if decision_result.risk_score > self.risk_threshold:
                return True
            
            # Check for boundary violations
            if any(check.violated for check in decision_result.boundary_checks):
                return True
            
            # Auto-approve low risk if configured
            if self.auto_approve_low_risk and decision_result.risk_score < 0.3:
                return False
            
        return False
    
    async def _notify_approval_required(self, request: ApprovalRequest):
        """
        Notify UI/user that approval is required
        """
        # In production, this would send websocket message or webhook
        logger.info(f"Approval required for task {request.task_id}")
        
        # Simulate notification
        notification = {
            "type": "approval_required",
            "task_id": request.task_id,
            "description": request.task_description,
            "confidence": request.confidence,
            "risk_score": request.risk_score,
            "timeout": request.timeout,
            "timestamp": request.created_at.isoformat()
        }
        
        # TODO: Send via websocket/webhook
        logger.debug(f"Notification: {json.dumps(notification)}")
    
    def _log_approval(
        self,
        task: DelegatedTask,
        request: ApprovalRequest,
        response: ApprovalResponse
    ):
        """
        Log approval decision to audit trail
        """
        try:
            with get_db() as db:
                audit = AuditLog(
                    persona_id=task.persona_id,
                    action_type="approval_decision",
                    action_category="hilt",
                    action_description=f"Approval decision for task {task.id}",
                    actor_type="user",
                    actor_id=response.approved_by,
                    before_state={
                        "task_status": task.status.value,
                        "decision": request.decision,
                        "confidence": request.confidence,
                        "risk_score": request.risk_score
                    },
                    after_state={
                        "approval_action": response.action.value,
                        "modified_decision": response.modified_decision,
                        "feedback": response.feedback,
                        "response_time": response.response_time
                    },
                    success=True
                )
                db.add(audit)
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to log approval: {str(e)}")

# Export main controller class
__all__ = ["HILTController", "HILTMode", "ApprovalRequest", "ApprovalResponse"]