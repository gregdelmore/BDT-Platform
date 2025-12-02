'''Audit Logger - Comprehensive audit logging'''
from typing import Dict, Any
from datetime import datetime
import logging
from ..database import get_db, AuditLog

logger = logging.getLogger(__name__)

class AuditLogger:
    def __init__(self, persona_id: str):
        self.persona_id = persona_id
    
    async def log_task_created(self, task):
        '''Log task creation'''
        await self._log("task_created", "task", f"Task {task.id} created", {"task_id": str(task.id)})
    
    async def log_decision_made(self, task, decision_result):
        '''Log decision made'''
        await self._log("decision_made", "decision", f"Decision for task {task.id}", {
            "task_id": str(task.id),
            "confidence": decision_result.confidence,
            "risk": decision_result.risk_score
        })
    
    async def log_boundary_check(self, task, result):
        '''Log boundary check'''
        await self._log("boundary_check", "boundary", f"Boundary check for task {task.id}", {
            "task_id": str(task.id),
            "allowed": result.get("allowed"),
            "violations": len(result.get("violations", []))
        })
    
    async def log_task_executed(self, task, result):
        '''Log task execution'''
        await self._log("task_executed", "execution", f"Task {task.id} executed", {
            "task_id": str(task.id),
            "success": result.get("success")
        })
    
    async def log_task_completed(self, task, result):
        '''Log task completion'''
        await self._log("task_completed", "completion", f"Task {task.id} completed", {
            "task_id": str(task.id),
            "success": result.get("success")
        })
    
    async def log_task_blocked(self, task, reason):
        '''Log task blocked'''
        await self._log("task_blocked", "blocking", f"Task {task.id} blocked: {reason}", {
            "task_id": str(task.id),
            "reason": reason
        })
    
    async def log_task_rejected(self, task, approval):
        '''Log task rejection'''
        await self._log("task_rejected", "rejection", f"Task {task.id} rejected", {
            "task_id": str(task.id),
            "feedback": approval.feedback
        })
    
    async def log_task_error(self, task, error):
        '''Log task error'''
        await self._log("task_error", "error", f"Task {task.id} error: {str(error)}", {
            "task_id": str(task.id),
            "error": str(error)
        })
    
    async def _log(self, action_type: str, category: str, description: str, data: Dict[str, Any]):
        '''Internal logging method'''
        try:
            with get_db() as db:
                log = AuditLog(
                    persona_id=self.persona_id,
                    action_type=action_type,
                    action_category=category,
                    action_description=description,
                    actor_type="agent",
                    actor_id=self.persona_id,
                    after_state=data,
                    success=True
                )
                db.add(log)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
