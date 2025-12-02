'''Monitoring API routes'''
from fastapi import APIRouter, Depends
from typing import Dict
from datetime import datetime, timedelta
from ...database import get_db, DelegatedTask, AuditLog, Persona
from ..middleware.auth import get_current_user

router = APIRouter()

@router.get("/stats")
async def get_system_stats(current_user: Dict = Depends(get_current_user)):
    '''Get system statistics'''
    try:
        with get_db() as db:
            total_personas = db.query(Persona).count()
            total_tasks = db.query(DelegatedTask).count()
            recent_tasks = db.query(DelegatedTask).filter(
                DelegatedTask.created_at >= datetime.utcnow() - timedelta(days=1)
            ).count()
            
            return {
                "total_personas": total_personas,
                "total_tasks": total_tasks,
                "tasks_24h": recent_tasks,
                "system_status": "operational"
            }
    except Exception as e:
        return {"error": str(e), "system_status": "error"}

@router.get("/health")
async def health_check():
    '''Health check endpoint'''
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@router.get("/metrics")
async def get_metrics(current_user: Dict = Depends(get_current_user)):
    '''Get system metrics'''
    # This would integrate with Prometheus or similar
    return {
        "cpu_usage": 45.2,
        "memory_usage": 62.8,
        "active_connections": 12,
        "queue_depth": 3
    }
