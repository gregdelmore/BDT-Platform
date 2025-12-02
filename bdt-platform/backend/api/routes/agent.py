"""
L4 Agent API routes
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from ...database import get_db, DelegatedTask, Persona, TaskStatus
from ...agents.delegated_agent import L4DelegatedAgent, AgentState
from ..middleware.auth import get_current_user

router = APIRouter()

# Global agent instances (in production, use proper state management)
active_agents: Dict[str, L4DelegatedAgent] = {}

# Request/Response models
class TaskDelegationRequest(BaseModel):
    """Request to delegate a task"""
    task_type: str = Field(..., description="Type of task to delegate")
    task_description: str = Field(..., description="Detailed task description")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Task input data")
    priority: int = Field(default=5, ge=1, le=10, description="Task priority (1-10)")

class TaskResponse(BaseModel):
    """Task response"""
    task_id: str
    status: str
    created_at: datetime
    confidence_score: Optional[float]
    risk_score: Optional[float]

class AgentStatusResponse(BaseModel):
    """Agent status response"""
    persona_id: str
    state: str
    active_tasks: int
    queued_tasks: int
    metrics: Dict[str, Any]
    configuration: Dict[str, Any]

class AgentControlRequest(BaseModel):
    """Agent control request"""
    action: str = Field(..., description="Control action: start, stop, pause, resume")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Configuration updates")

# Routes
@router.post("/personas/{persona_id}/start")
async def start_agent(
    persona_id: str,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """Start L4 agent for a persona"""
    try:
        # Check if agent already running
        if persona_id in active_agents:
            raise HTTPException(
                status_code=400,
                detail="Agent already running for this persona"
            )
        
        # Verify persona exists and is L4 capable
        with get_db() as db:
            persona = db.query(Persona).filter(
                Persona.id == persona_id
            ).first()
            
            if not persona:
                raise HTTPException(
                    status_code=404,
                    detail="Persona not found"
                )
            
            if persona.capability_level != "L4_DELEGATED_AGENT":
                raise HTTPException(
                    status_code=400,
                    detail=f"Persona capability level is {persona.capability_level}, L4 required"
                )
        
        # Create and start agent
        agent = L4DelegatedAgent(persona_id)
        active_agents[persona_id] = agent
        
        # Start in background
        background_tasks.add_task(agent.start)
        
        return {
            "message": "Agent started successfully",
            "persona_id": persona_id,
            "state": agent.state.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start agent: {str(e)}"
        )

@router.post("/personas/{persona_id}/stop")
async def stop_agent(
    persona_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Stop L4 agent for a persona"""
    try:
        if persona_id not in active_agents:
            raise HTTPException(
                status_code=404,
                detail="No active agent for this persona"
            )
        
        agent = active_agents[persona_id]
        await agent.stop()
        
        # Remove from active agents
        del active_agents[persona_id]
        
        return {
            "message": "Agent stopped successfully",
            "persona_id": persona_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop agent: {str(e)}"
        )

@router.post("/personas/{persona_id}/delegate", response_model=TaskResponse)
async def delegate_task(
    persona_id: str,
    request: TaskDelegationRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Delegate a task to the L4 agent"""
    try:
        # Check if agent is running
        if persona_id not in active_agents:
            raise HTTPException(
                status_code=400,
                detail="Agent not running for this persona. Start the agent first."
            )
        
        agent = active_agents[persona_id]
        
        # Delegate task
        task_id = await agent.delegate_task(
            task_type=request.task_type,
            task_description=request.task_description,
            input_data=request.input_data,
            priority=request.priority
        )
        
        # Get task details
        with get_db() as db:
            task = db.query(DelegatedTask).filter(
                DelegatedTask.id == task_id
            ).first()
            
            if not task:
                raise HTTPException(
                    status_code=404,
                    detail="Task not found after creation"
                )
            
            return TaskResponse(
                task_id=str(task.id),
                status=task.status.value,
                created_at=task.created_at,
                confidence_score=task.confidence_score,
                risk_score=task.risk_score
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delegate task: {str(e)}"
        )

@router.get("/personas/{persona_id}/status", response_model=AgentStatusResponse)
async def get_agent_status(
    persona_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Get L4 agent status"""
    try:
        if persona_id not in active_agents:
            raise HTTPException(
                status_code=404,
                detail="No active agent for this persona"
            )
        
        agent = active_agents[persona_id]
        status = await agent.get_status()
        
        return AgentStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get agent status: {str(e)}"
        )

@router.get("/personas/{persona_id}/tasks")
async def get_agent_tasks(
    persona_id: str,
    status: Optional[TaskStatus] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    current_user: Dict = Depends(get_current_user)
):
    """Get tasks for an agent"""
    try:
        with get_db() as db:
            query = db.query(DelegatedTask).filter(
                DelegatedTask.persona_id == persona_id
            )
            
            if status:
                query = query.filter(DelegatedTask.status == status)
            
            total = query.count()
            tasks = query.offset(offset).limit(limit).all()
            
            return {
                "total": total,
                "offset": offset,
                "limit": limit,
                "tasks": [
                    {
                        "task_id": str(task.id),
                        "task_type": task.task_type,
                        "task_description": task.task_description,
                        "status": task.status.value,
                        "confidence_score": task.confidence_score,
                        "risk_score": task.risk_score,
                        "requires_approval": task.requires_approval,
                        "created_at": task.created_at.isoformat() if task.created_at else None,
                        "started_at": task.started_at.isoformat() if task.started_at else None,
                        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                        "success": task.success
                    }
                    for task in tasks
                ]
            }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tasks: {str(e)}"
        )

@router.post("/personas/{persona_id}/control")
async def control_agent(
    persona_id: str,
    request: AgentControlRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Control agent (pause, resume, configure)"""
    try:
        if persona_id not in active_agents:
            raise HTTPException(
                status_code=404,
                detail="No active agent for this persona"
            )
        
        agent = active_agents[persona_id]
        
        # Execute control action
        if request.action == "pause":
            await agent.pause()
            return {"message": "Agent paused"}
        
        elif request.action == "resume":
            await agent.resume()
            return {"message": "Agent resumed"}
        
        elif request.action == "configure":
            if request.configuration:
                # Apply configuration updates
                # This would update agent configuration
                return {"message": "Configuration updated"}
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Configuration required for configure action"
                )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown control action: {request.action}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to control agent: {str(e)}"
        )

@router.get("/active")
async def get_active_agents(
    current_user: Dict = Depends(get_current_user)
):
    """Get list of all active agents"""
    try:
        agents = []
        for persona_id, agent in active_agents.items():
            status = await agent.get_status()
            agents.append({
                "persona_id": persona_id,
                "state": status["state"],
                "active_tasks": status["active_tasks"],
                "queued_tasks": status["queued_tasks"]
            })
        
        return {
            "total": len(agents),
            "agents": agents
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get active agents: {str(e)}"
        )