'''Boundary Enforcer - Enforces negative space boundaries'''
from typing import Dict, List, Any
import logging
from ..database import get_db, NegativeSpaceBoundary
from ..core.negative_space import NegativeSpaceAnalyzer

logger = logging.getLogger(__name__)

class BoundaryEnforcer:
    def __init__(self, persona_id: str):
        self.persona_id = persona_id
        self.analyzer = NegativeSpaceAnalyzer()
    
    async def check_task_boundaries(self, task, decision_result) -> Dict[str, Any]:
        '''Check if task violates boundaries'''
        boundary_checks = self.analyzer.check_boundaries(
            self.persona_id, task, {"timestamp": datetime.utcnow()}
        )
        
        violations = [c for c in boundary_checks if c.violated]
        
        return {
            "allowed": len(violations) == 0,
            "violations": violations,
            "reason": violations[0].recommendation if violations else None
        }
    
    async def adjust_boundary(self, boundary_id: str, adjustment: Dict):
        '''Adjust boundary based on learning'''
        return self.analyzer.update_boundary_confidence(
            boundary_id, adjustment.get("feedback", ""), adjustment.get("confidence_change", 0)
        )
