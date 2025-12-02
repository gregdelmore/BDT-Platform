"""
Human-in-the-Loop (HILT) Controller
Manages approval workflows, escalation, and action execution
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import asyncio
import json
import uuid

from core.config import settings
from core.models import (
    HILTAction, 
    PersonaModel, 
    ApprovalStatus, 
    RiskLevel,
    AuditLog
)
from services.risk_assessment import RiskAssessmentEngine
from services.negative_space import NegativeSpaceAnalyzer

class HILTController:
    """
    Central controller for Human-in-the-Loop approval workflows.
    Manages the complete lifecycle of L3 guided actions.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.risk_engine = RiskAssessmentEngine()
        self.negative_space = NegativeSpaceAnalyzer(db)
        
        # Configuration
        self.auto_approve_threshold = settings.HILT_AUTO_APPROVE_THRESHOLD
        self.auto_reject_threshold = settings.HILT_AUTO_REJECT_THRESHOLD
        self.escalation_timeout = settings.HILT_ESCALATION_TIMEOUT
        
        # In-memory state for active approvals
        self.pending_approvals = {}
        self.escalation_timers = {}
        
    async def submit_for_approval(
        self,
        persona_id: int,
        action_type: str,
        action_payload: Dict[str, Any],
        original_query: str,
        supporting_evidence: Optional[List[Dict]] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Submit an action for HILT approval
        
        Returns:
            Dictionary with approval status and details
        """
        
        # Validate persona
        persona = self.db.query(PersonaModel).filter_by(id=persona_id).first()
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")
        
        # Check negative space boundaries
        boundary_check = self.negative_space.check_boundary_violation(
            persona_id, 
            action_payload
        )
        
        if boundary_check and boundary_check["violated"]:
            primary_violation = boundary_check["primary_violation"]
            
            # Check if override is allowed
            if not primary_violation["override_allowed"]:
                # Immediate rejection for non-overridable boundaries
                return {
                    "status": "rejected",
                    "reason": f"Violates non-overridable boundary: {primary_violation['pattern']}",
                    "risk_level": primary_violation["risk_level"],
                    "boundary_violation": boundary_check,
                    "action_id": None
                }
        
        # Assess risk
        risk_score, risk_level, risk_details = await self.risk_engine.assess_action_risk(
            action_payload,
            persona,
            context
        )
        
        # Calculate confidence
        confidence_score = await self.risk_engine.calculate_confidence_score(
            action_payload,
            persona,
            supporting_evidence or []
        )
        
        # Determine initial status
        status = self._determine_initial_status(
            confidence_score,
            risk_score,
            risk_level,
            boundary_check
        )
        
        # Create HILT action record
        hilt_action = HILTAction(
            persona_id=persona_id,
            action_type=action_type,
            action_payload=action_payload,
            original_query=original_query,
            context=context,
            confidence_score=confidence_score,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=risk_details["factors"],
            status=status,
            expires_at=datetime.utcnow() + timedelta(seconds=self.escalation_timeout)
        )
        
        # Handle auto-approval/rejection
        if status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]:
            hilt_action.approved_at = datetime.utcnow()
            hilt_action.approved_by = "SYSTEM_AUTO"
            
            if status == ApprovalStatus.REJECTED:
                hilt_action.rejection_reason = self._generate_rejection_reason(
                    confidence_score,
                    risk_score,
                    boundary_check
                )
        
        self.db.add(hilt_action)
        self.db.commit()
        
        # Add to pending queue if manual review needed
        if status == ApprovalStatus.PENDING:
            self._add_to_pending_queue(hilt_action, risk_details, boundary_check)
            
            # Start escalation timer
            asyncio.create_task(self._start_escalation_timer(hilt_action.id))
        
        # Create response
        response = {
            "action_id": hilt_action.id,
            "status": status.value,
            "confidence_score": confidence_score,
            "risk_score": risk_score,
            "risk_level": risk_level.value,
            "risk_details": risk_details,
            "auto_processed": status != ApprovalStatus.PENDING,
            "requires_approval": status == ApprovalStatus.PENDING
        }
        
        if status == ApprovalStatus.PENDING:
            response["expires_at"] = hilt_action.expires_at.isoformat()
            response["time_remaining"] = self.escalation_timeout
        
        if boundary_check:
            response["boundary_warning"] = boundary_check
        
        # Log submission
        self._log_action_submission(hilt_action, response)
        
        return response
    
    def _determine_initial_status(
        self,
        confidence: float,
        risk: float,
        risk_level: RiskLevel,
        boundary_check: Optional[Dict]
    ) -> ApprovalStatus:
        """Determine initial approval status based on scores"""
        
        # Auto-reject conditions
        if confidence <= self.auto_reject_threshold:
            return ApprovalStatus.REJECTED
        
        if risk >= 0.9 or risk_level == RiskLevel.CRITICAL:
            return ApprovalStatus.REJECTED
        
        if boundary_check and boundary_check["violated"]:
            if boundary_check["total_violations"] > 2:
                return ApprovalStatus.REJECTED
        
        # Auto-approve conditions
        if confidence >= self.auto_approve_threshold and risk < 0.3:
            if not boundary_check or not boundary_check["violated"]:
                return ApprovalStatus.APPROVED
        
        # Default to pending for manual review
        return ApprovalStatus.PENDING
    
    async def approve_action(
        self,
        action_id: int,
        approved_by: str,
        modifications: Optional[Dict] = None,
        override_boundaries: bool = False
    ) -> Dict[str, Any]:
        """Approve a pending HILT action"""
        
        action = self.db.query(HILTAction).filter_by(id=action_id).first()
        if not action:
            raise ValueError(f"Action {action_id} not found")
        
        if action.status != ApprovalStatus.PENDING:
            raise ValueError(f"Action {action_id} is not pending approval (status: {action.status.value})")
        
        # Check expiration
        if datetime.utcnow() > action.expires_at:
            action.status = ApprovalStatus.EXPIRED
            self.db.commit()
            raise ValueError(f"Action {action_id} has expired")
        
        # Update action
        if modifications:
            action.modified_payload = modifications
            action.status = ApprovalStatus.MODIFIED
        else:
            action.status = ApprovalStatus.APPROVED
        
        action.approved_by = approved_by
        action.approved_at = datetime.utcnow()
        action.response_time_seconds = (action.approved_at - action.created_at).total_seconds()
        
        self.db.commit()
        
        # Remove from pending queue
        self._remove_from_pending_queue(action_id)
        
        # Cancel escalation timer
        self._cancel_escalation_timer(action_id)
        
        # Execute the action
        execution_result = await self._execute_action(action, override_boundaries)
        
        # Log approval
        self._log_action_approval(action, approved_by, modifications)
        
        return {
            "action_id": action_id,
            "status": action.status.value,
            "approved_by": approved_by,
            "approved_at": action.approved_at.isoformat(),
            "modifications": modifications,
            "execution_result": execution_result,
            "response_time": action.response_time_seconds
        }
    
    async def reject_action(
        self,
        action_id: int,
        rejected_by: str,
        reason: str,
        update_boundaries: bool = False
    ) -> Dict[str, Any]:
        """Reject a pending HILT action"""
        
        action = self.db.query(HILTAction).filter_by(id=action_id).first()
        if not action:
            raise ValueError(f"Action {action_id} not found")
        
        if action.status != ApprovalStatus.PENDING:
            raise ValueError(f"Action {action_id} is not pending approval")
        
        # Update action
        action.status = ApprovalStatus.REJECTED
        action.approved_by = rejected_by
        action.approved_at = datetime.utcnow()
        action.rejection_reason = reason
        action.response_time_seconds = (action.approved_at - action.created_at).total_seconds()
        
        self.db.commit()
        
        # Remove from pending queue
        self._remove_from_pending_queue(action_id)
        
        # Cancel escalation timer
        self._cancel_escalation_timer(action_id)
        
        # Update negative space boundaries if requested
        if update_boundaries:
            await self._update_boundaries_from_rejection(action, reason)
        
        # Log rejection
        self._log_action_rejection(action, rejected_by, reason)
        
        return {
            "action_id": action_id,
            "status": action.status.value,
            "rejected_by": rejected_by,
            "rejected_at": action.approved_at.isoformat(),
            "reason": reason,
            "boundaries_updated": update_boundaries,
            "response_time": action.response_time_seconds
        }
    
    async def suggest_alternative(
        self,
        action_id: int,
        suggested_by: str,
        alternative_action: Dict[str, Any],
        reason: str
    ) -> Dict[str, Any]:
        """Suggest an alternative action"""
        
        original = self.db.query(HILTAction).filter_by(id=action_id).first()
        if not original:
            raise ValueError(f"Action {action_id} not found")
        
        # Create new action based on alternative
        result = await self.submit_for_approval(
            persona_id=original.persona_id,
            action_type=alternative_action.get("action_type", original.action_type),
            action_payload=alternative_action,
            original_query=f"{original.original_query} [Alternative to #{action_id}]",
            context={"original_action_id": action_id, "suggestion_reason": reason}
        )
        
        # Link the alternative
        if result["action_id"]:
            new_action = self.db.query(HILTAction).filter_by(id=result["action_id"]).first()
            if new_action:
                new_action.context = new_action.context or {}
                new_action.context["alternative_to"] = action_id
                new_action.context["suggested_by"] = suggested_by
                self.db.commit()
        
        return result
    
    async def escalate_action(
        self,
        action_id: int,
        escalation_reason: str,
        escalate_to: Optional[str] = None
    ):
        """Manually escalate an action"""
        
        action = self.db.query(HILTAction).filter_by(id=action_id).first()
        if not action:
            raise ValueError(f"Action {action_id} not found")
        
        # Update action
        action.status = ApprovalStatus.ESCALATED
        action.escalated = True
        action.escalation_reason = escalation_reason
        action.escalated_at = datetime.utcnow()
        
        # Determine escalation target
        if escalate_to:
            action.escalated_to = escalate_to
        else:
            action.escalated_to = self._determine_escalation_target(action)
        
        self.db.commit()
        
        # Notify escalation target
        await self._send_escalation_notification(action)
        
        return {
            "action_id": action_id,
            "escalated_to": action.escalated_to,
            "reason": escalation_reason,
            "escalated_at": action.escalated_at.isoformat()
        }
    
    def get_pending_approvals(
        self,
        persona_id: Optional[int] = None,
        include_risk_details: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all pending approvals"""
        
        query = self.db.query(HILTAction).filter_by(status=ApprovalStatus.PENDING)
        
        if persona_id:
            query = query.filter_by(persona_id=persona_id)
        
        pending = query.order_by(HILTAction.created_at.desc()).all()
        
        results = []
        for action in pending:
            item = {
                "action_id": action.id,
                "persona_id": action.persona_id,
                "action_type": action.action_type,
                "original_query": action.original_query,
                "confidence_score": action.confidence_score,
                "risk_score": action.risk_score,
                "risk_level": action.risk_level.value,
                "created_at": action.created_at.isoformat(),
                "expires_at": action.expires_at.isoformat(),
                "time_remaining": max(0, (action.expires_at - datetime.utcnow()).total_seconds())
            }
            
            if include_risk_details and action.id in self.pending_approvals:
                item["risk_details"] = self.pending_approvals[action.id].get("risk_details")
                item["boundary_warning"] = self.pending_approvals[action.id].get("boundary_warning")
            
            results.append(item)
        
        return results
    
    def get_action_status(self, action_id: int) -> Dict[str, Any]:
        """Get current status of an action"""
        
        action = self.db.query(HILTAction).filter_by(id=action_id).first()
        if not action:
            raise ValueError(f"Action {action_id} not found")
        
        return {
            "action_id": action.id,
            "status": action.status.value,
            "confidence_score": action.confidence_score,
            "risk_score": action.risk_score,
            "risk_level": action.risk_level.value,
            "created_at": action.created_at.isoformat(),
            "approved_at": action.approved_at.isoformat() if action.approved_at else None,
            "approved_by": action.approved_by,
            "execution_result": action.execution_result,
            "execution_error": action.execution_error
        }
    
    def get_approval_statistics(
        self,
        persona_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get HILT approval statistics"""
        
        since = datetime.utcnow() - timedelta(days=days)
        
        actions = (
            self.db.query(HILTAction)
            .filter_by(persona_id=persona_id)
            .filter(HILTAction.created_at >= since)
            .all()
        )
        
        if not actions:
            return {
                "persona_id": persona_id,
                "period_days": days,
                "total_actions": 0,
                "no_data": True
            }
        
        # Calculate statistics
        stats = {
            "persona_id": persona_id,
            "period_days": days,
            "total_actions": len(actions),
            "status_distribution": {
                "approved": len([a for a in actions if a.status == ApprovalStatus.APPROVED]),
                "rejected": len([a for a in actions if a.status == ApprovalStatus.REJECTED]),
                "pending": len([a for a in actions if a.status == ApprovalStatus.PENDING]),
                "escalated": len([a for a in actions if a.status == ApprovalStatus.ESCALATED]),
                "modified": len([a for a in actions if a.status == ApprovalStatus.MODIFIED]),
                "expired": len([a for a in actions if a.status == ApprovalStatus.EXPIRED])
            },
            "auto_processed": {
                "count": len([
                    a for a in actions 
                    if a.status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]
                    and a.approved_by == "SYSTEM_AUTO"
                ]),
                "percentage": 0
            },
            "risk_distribution": {
                "low": len([a for a in actions if a.risk_level == RiskLevel.LOW]),
                "medium": len([a for a in actions if a.risk_level == RiskLevel.MEDIUM]),
                "high": len([a for a in actions if a.risk_level == RiskLevel.HIGH]),
                "critical": len([a for a in actions if a.risk_level == RiskLevel.CRITICAL])
            },
            "average_confidence": np.mean([a.confidence_score for a in actions]),
            "average_risk": np.mean([a.risk_score for a in actions]),
            "average_response_time": self._calculate_avg_response_time(actions)
        }
        
        stats["auto_processed"]["percentage"] = (
            stats["auto_processed"]["count"] / stats["total_actions"] * 100
            if stats["total_actions"] > 0 else 0
        )
        
        return stats
    
    # Helper methods
    def _add_to_pending_queue(
        self,
        action: HILTAction,
        risk_details: Dict,
        boundary_check: Optional[Dict]
    ):
        """Add action to pending approval queue"""
        
        self.pending_approvals[action.id] = {
            "action": action,
            "risk_details": risk_details,
            "boundary_warning": boundary_check,
            "added_at": datetime.utcnow()
        }
    
    def _remove_from_pending_queue(self, action_id: int):
        """Remove action from pending queue"""
        
        if action_id in self.pending_approvals:
            del self.pending_approvals[action_id]
    
    def _cancel_escalation_timer(self, action_id: int):
        """Cancel escalation timer for an action"""
        
        if action_id in self.escalation_timers:
            self.escalation_timers[action_id].cancel()
            del self.escalation_timers[action_id]
    
    async def _start_escalation_timer(self, action_id: int):
        """Start escalation timer for an action"""
        
        try:
            # Wait for timeout period
            await asyncio.sleep(self.escalation_timeout)
            
            # Check if action is still pending
            action = self.db.query(HILTAction).filter_by(id=action_id).first()
            if action and action.status == ApprovalStatus.PENDING:
                await self._auto_escalate(action)
                
        except asyncio.CancelledError:
            # Timer was cancelled (action was approved/rejected)
            pass
    
    async def _auto_escalate(self, action: HILTAction):
        """Automatically escalate an expired action"""
        
        action.status = ApprovalStatus.ESCALATED
        action.escalated = True
        action.escalation_reason = "Timeout - no response within configured window"
        action.escalated_at = datetime.utcnow()
        action.escalated_to = self._determine_escalation_target(action)
        
        self.db.commit()
        
        # Remove from pending queue
        self._remove_from_pending_queue(action.id)
        
        # Send notification
        await self._send_escalation_notification(action)
    
    def _determine_escalation_target(self, action: HILTAction) -> str:
        """Determine who to escalate to based on risk"""
        
        if action.risk_level == RiskLevel.CRITICAL:
            return "executive_team"
        elif action.risk_level == RiskLevel.HIGH:
            return "senior_management"
        elif action.risk_level == RiskLevel.MEDIUM:
            return "team_lead"
        else:
            return "supervisor"
    
    async def _execute_action(
        self,
        action: HILTAction,
        override_boundaries: bool = False
    ) -> Dict[str, Any]:
        """Execute an approved action"""
        
        try:
            # Get the appropriate payload
            payload = action.modified_payload if action.modified_payload else action.action_payload
            
            # Import action executor dynamically
            from services.action_executor import ActionExecutor
            
            executor = ActionExecutor(self.db)
            result = await executor.execute(
                action_type=action.action_type,
                payload=payload,
                persona_id=action.persona_id,
                override_boundaries=override_boundaries
            )
            
            # Update action record
            action.executed_at = datetime.utcnow()
            action.execution_result = result
            action.execution_success = result.get("success", False)
            
            self.db.commit()
            
            return result
            
        except Exception as e:
            action.execution_error = str(e)
            action.execution_success = False
            self.db.commit()
            raise
    
    async def _update_boundaries_from_rejection(
        self,
        action: HILTAction,
        reason: str
    ):
        """Update negative space boundaries based on rejection"""
        
        from core.models import NegativeSpace
        
        # Create new boundary
        new_boundary = NegativeSpace(
            persona_id=action.persona_id,
            category="tasks",
            pattern=f"Rejected: {action.action_type}",
            description=f"Action rejected: {reason}",
            risk_level=action.risk_level,
            evidence_count=1,
            confidence=0.6,
            override_allowed=True
        )
        
        self.db.add(new_boundary)
        self.db.commit()
    
    async def _send_escalation_notification(self, action: HILTAction):
        """Send escalation notification"""
        
        # This would integrate with notification system
        notification_data = {
            "action_id": action.id,
            "escalated_to": action.escalated_to,
            "risk_level": action.risk_level.value,
            "reason": action.escalation_reason,
            "created_at": action.created_at.isoformat(),
            "escalated_at": action.escalated_at.isoformat()
        }
        
        # Log the escalation
        print(f"ESCALATION: Action {action.id} escalated to {action.escalated_to}")
        
        # In production, this would send emails/Slack/Teams notifications
    
    def _calculate_avg_response_time(self, actions: List[HILTAction]) -> float:
        """Calculate average response time for approved/rejected actions"""
        
        response_times = []
        
        for action in actions:
            if action.response_time_seconds:
                response_times.append(action.response_time_seconds)
        
        if response_times:
            import numpy as np
            return float(np.mean(response_times))
        
        return 0.0
    
    def _generate_rejection_reason(
        self,
        confidence: float,
        risk: float,
        boundary_check: Optional[Dict]
    ) -> str:
        """Generate automatic rejection reason"""
        
        reasons = []
        
        if confidence <= self.auto_reject_threshold:
            reasons.append(f"Confidence too low ({confidence:.2f})")
        
        if risk >= 0.9:
            reasons.append(f"Risk too high ({risk:.2f})")
        
        if boundary_check and boundary_check["violated"]:
            reasons.append(f"Violates boundaries: {boundary_check['total_violations']} violations")
        
        return " | ".join(reasons) if reasons else "Auto-rejected based on risk assessment"
    
    # Logging methods
    def _log_action_submission(self, action: HILTAction, response: Dict):
        """Log action submission"""
        
        audit_log = AuditLog(
            persona_id=action.persona_id,
            action_id=action.id,
            event_type="hilt_submission",
            event_category="approval_workflow",
            event_data={
                "action_type": action.action_type,
                "status": response["status"],
                "confidence": response["confidence_score"],
                "risk": response["risk_score"]
            },
            user_email="system"
        )
        self.db.add(audit_log)
        self.db.commit()
    
    def _log_action_approval(self, action: HILTAction, approved_by: str, modifications: Optional[Dict]):
        """Log action approval"""
        
        audit_log = AuditLog(
            persona_id=action.persona_id,
            action_id=action.id,
            event_type="hilt_approval",
            event_category="approval_workflow",
            event_data={
                "approved_by": approved_by,
                "modifications": modifications is not None,
                "response_time": action.response_time_seconds
            },
            user_email=approved_by
        )
        self.db.add(audit_log)
        self.db.commit()
    
    def _log_action_rejection(self, action: HILTAction, rejected_by: str, reason: str):
        """Log action rejection"""
        
        audit_log = AuditLog(
            persona_id=action.persona_id,
            action_id=action.id,
            event_type="hilt_rejection",
            event_category="approval_workflow",
            event_data={
                "rejected_by": rejected_by,
                "reason": reason,
                "response_time": action.response_time_seconds
            },
            user_email=rejected_by
        )
        self.db.add(audit_log)
        self.db.commit()
