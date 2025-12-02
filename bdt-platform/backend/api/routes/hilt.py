"""
HILT (Human-in-the-Loop) Control API routes
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from ...database import get_db, DelegatedTask, ApprovalAction
from ...core.hilt_controller import HILTController, HILTMode
from ..middleware.auth import get_current_user

router = APIRouter()

# Global HILT controller (in production, use proper state management)
hilt_controller = HILTController()

# Request/Response models
class ApprovalSubmission(BaseModel):
    """Approval submission request"""
    action: str = Field(..., description="Approval action: APPROVE, REJECT, MODIFY, DELEGATE")
    modified_decision: Optional[str] = Field(None, description="Modified decision if action is MODIFY")
    feedback: Optional[str] = Field(None, description="Feedback for the decision")
    delegate_to: Optional[str] = Field(None, description="Delegate to person/system if action is DELEGATE")

class HILTModeUpdate(BaseModel):
    """HILT mode update request"""
    mode: str = Field(..., description="HILT mode: full_auto, selective, guided, learning")
    persona_id: Optional[str] = Field(None, description="Apply to specific persona or global if None")

class PendingApprovalResponse(BaseModel):
    """Pending approval response"""
    task_id: str
    task_description: str
    decision: str
    confidence: float
    risk_score: float
    reasoning: List[str]
    boundary_concerns: List[Dict]
    created_at: datetime
    timeout_at: datetime

# Routes
@router.get("/approvals/pending", response_model=List[PendingApprovalResponse])
async def get_pending_approvals(
    persona_id: Optional[str] = Query(None),
    current_user: Dict = Depends(get_current_user)
):
    """Get pending approval requests"""
    try:
        pending = hilt_controller.get_pending_approvals(persona_id)
        
        return [
            PendingApprovalResponse(
                task_id=p["task_id"],
                task_description=p["task_description"],
                decision=p["decision"],
                confidence=p["confidence"],
                risk_score=p["risk_score"],
                reasoning=p["reasoning"],
                boundary_concerns=p["boundary_concerns"],
                created_at=datetime.fromisoformat(p["created_at"]),
                timeout_at=datetime.fromisoformat(p["timeout_at"])
            )
            for p in pending
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pending approvals: {str(e)}"
        )

@router.post("/approvals/{task_id}/submit")
async def submit_approval(
    task_id: str,
    submission: ApprovalSubmission,
    current_user: Dict = Depends(get_current_user)
):
    """Submit approval decision for a task"""
    try:
        # Convert string action to enum
        action = ApprovalAction[submission.action]
        
        # Submit approval
        success = await hilt_controller.submit_approval(
            task_id=task_id,
            action=action,
            approved_by=current_user.get("email", "unknown"),
            modified_decision=submission.modified_decision,
            feedback=submission.feedback,
            delegate_to=submission.delegate_to
        )
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to submit approval - task may not be pending"
            )
        
        return {
            "message": "Approval submitted successfully",
            "task_id": task_id,
            "action": submission.action
        }
        
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid approval action: {submission.action}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit approval: {str(e)}"
        )

@router.put("/mode")
async def update_hilt_mode(
    update: HILTModeUpdate,
    current_user: Dict = Depends(get_current_user)
):
    """Update HILT operation mode"""
    try:
        # Convert string mode to enum
        mode = HILTMode[update.mode.upper()]
        
        # Set mode
        hilt_controller.set_mode(mode, update.persona_id)
        
        return {
            "message": "HILT mode updated successfully",
            "mode": update.mode,
            "persona_id": update.persona_id,
            "scope": "persona" if update.persona_id else "global"
        }
        
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid HILT mode: {update.mode}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update HILT mode: {str(e)}"
        )

@router.get("/mode")
async def get_hilt_mode(
    persona_id: Optional[str] = Query(None),
    current_user: Dict = Depends(get_current_user)
):
    """Get current HILT mode"""
    try:
        if persona_id:
            # Get persona-specific mode
            with get_db() as db:
                from ...database import Persona
                persona = db.query(Persona).filter(
                    Persona.id == persona_id
                ).first()
                
                if not persona:
                    raise HTTPException(
                        status_code=404,
                        detail="Persona not found"
                    )
                
                mode = persona.config.get("hilt_mode", "selective") if persona.config else "selective"
        else:
            # Get global mode
            mode = hilt_controller.mode.value
        
        return {
            "mode": mode,
            "persona_id": persona_id,
            "scope": "persona" if persona_id else "global"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get HILT mode: {str(e)}"
        )

@router.get("/statistics/{persona_id}")
async def get_approval_statistics(
    persona_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user: Dict = Depends(get_current_user)
):
    """Get approval statistics for a persona"""
    try:
        stats = hilt_controller.get_approval_statistics(persona_id, days)
        
        return {
            "persona_id": persona_id,
            "period_days": days,
            "statistics": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get approval statistics: {str(e)}"
        )

@router.post("/approvals/{task_id}/expedite")
async def expedite_approval(
    task_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Expedite an approval (reduce timeout)"""
    try:
        # This would reduce the timeout for urgent approvals
        # For now, return success
        return {
            "message": "Approval expedited",
            "task_id": task_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to expedite approval: {str(e)}"
        )

@router.get("/thresholds")
async def get_hilt_thresholds(
    current_user: Dict = Depends(get_current_user)
):
    """Get HILT approval thresholds"""
    try:
        return {
            "confidence_threshold": hilt_controller.confidence_threshold,
            "risk_threshold": hilt_controller.risk_threshold,
            "auto_approve_low_risk": hilt_controller.auto_approve_low_risk,
            "approval_timeout": hilt_controller.approval_timeout
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get thresholds: {str(e)}"
        )

@router.put("/thresholds")
async def update_hilt_thresholds(
    confidence_threshold: Optional[float] = Query(None, ge=0, le=1),
    risk_threshold: Optional[float] = Query(None, ge=0, le=1),
    auto_approve_low_risk: Optional[bool] = Query(None),
    approval_timeout: Optional[int] = Query(None, ge=60, le=3600),
    current_user: Dict = Depends(get_current_user)
):
    """Update HILT approval thresholds"""
    try:
        if confidence_threshold is not None:
            hilt_controller.confidence_threshold = confidence_threshold
        
        if risk_threshold is not None:
            hilt_controller.risk_threshold = risk_threshold
        
        if auto_approve_low_risk is not None:
            hilt_controller.auto_approve_low_risk = auto_approve_low_risk
        
        if approval_timeout is not None:
            hilt_controller.approval_timeout = approval_timeout
        
        return {
            "message": "Thresholds updated successfully",
            "confidence_threshold": hilt_controller.confidence_threshold,
            "risk_threshold": hilt_controller.risk_threshold,
            "auto_approve_low_risk": hilt_controller.auto_approve_low_risk,
            "approval_timeout": hilt_controller.approval_timeout
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update thresholds: {str(e)}"
        )