'''Ontology API routes'''
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from pydantic import BaseModel, Field
from ...database import get_db, Persona, OntologyMapping
from ...core.ontology_engine import FourthOntologyEngine
from ..middleware.auth import get_current_user

router = APIRouter()

class OntologyUpdate(BaseModel):
    dimension: str = Field(..., description="Dimension to update")
    value: float = Field(..., ge=0, le=100)
    reason: str = Field(..., description="Reason for update")

@router.get("/personas/{persona_id}/ontology")
async def get_ontology(
    persona_id: str,
    current_user: Dict = Depends(get_current_user)
):
    '''Get ontology mapping for a persona'''
    try:
        with get_db() as db:
            ontology = db.query(OntologyMapping).filter(
                OntologyMapping.persona_id == persona_id
            ).first()
            
            if not ontology:
                raise HTTPException(status_code=404, detail="Ontology not found")
            
            return {
                "persona_id": persona_id,
                "dimensions": {
                    "decisions": ontology.decisions_value,
                    "power": ontology.power_value,
                    "fear": ontology.fear_value,
                    "reward": ontology.reward_value,
                    "meaning": ontology.meaning_value
                },
                "confidence": {
                    "decisions": ontology.decisions_confidence,
                    "power": ontology.power_confidence,
                    "fear": ontology.fear_confidence,
                    "reward": ontology.reward_confidence,
                    "meaning": ontology.meaning_confidence
                },
                "last_calculated": ontology.last_calculated
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/personas/{persona_id}/ontology")
async def update_ontology(
    persona_id: str,
    update: OntologyUpdate,
    current_user: Dict = Depends(get_current_user)
):
    '''Update ontology dimension for a persona'''
    try:
        engine = FourthOntologyEngine()
        success = engine.adjust_dimension(
            persona_id,
            update.dimension,
            update.value,
            update.reason
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update ontology")
        
        return {"message": "Ontology updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/personas/{persona_id}/ontology/extract")
async def extract_ontology(
    persona_id: str,
    current_user: Dict = Depends(get_current_user)
):
    '''Extract ontology from behavioral data'''
    try:
        engine = FourthOntologyEngine()
        # This would normally get data from database
        # For now, return placeholder
        return {
            "message": "Ontology extraction started",
            "persona_id": persona_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
