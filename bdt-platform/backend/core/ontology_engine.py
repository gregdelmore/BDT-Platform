"""
Fourth Ontology Engine - Core extraction and management
"""
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from dataclasses import dataclass, asdict
from enum import Enum

from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, validator

from ..config import settings
from ..database import (
    get_db, Persona, OntologyMapping, BehavioralPattern,
    NegativeSpaceBoundary, BoundaryRiskLevel
)

logger = logging.getLogger(__name__)

class OntologyDimension(str, Enum):
    """Fourth Ontology dimensions"""
    DECISIONS = "decisions"
    POWER = "power"
    FEAR = "fear"
    REWARD = "reward"
    MEANING = "meaning"

@dataclass
class DimensionAnalysis:
    """Analysis result for a single dimension"""
    dimension: OntologyDimension
    value: float  # 0-100 scale
    confidence: float  # 0-1 scale
    evidence_count: int
    patterns: List[str]
    metadata: Dict[str, Any]

class OntologyExtraction(BaseModel):
    """Pydantic model for LLM extraction"""
    decisions_value: float = Field(..., ge=0, le=100, description="Analysis depth score")
    decisions_patterns: List[str] = Field(..., description="Decision-making patterns observed")
    
    power_value: float = Field(..., ge=0, le=100, description="Autonomy preference score")
    power_patterns: List[str] = Field(..., description="Power/control patterns observed")
    
    fear_value: float = Field(..., ge=0, le=100, description="Risk avoidance score")
    fear_patterns: List[str] = Field(..., description="Fear/safety patterns observed")
    
    reward_value: float = Field(..., ge=0, le=100, description="Motivation response score")
    reward_patterns: List[str] = Field(..., description="Reward/achievement patterns observed")
    
    meaning_value: float = Field(..., ge=0, le=100, description="Value alignment score")
    meaning_patterns: List[str] = Field(..., description="Meaning/purpose patterns observed")
    
    confidence_scores: Dict[str, float] = Field(..., description="Confidence for each dimension")
    
    @validator("confidence_scores")
    def validate_confidence(cls, v):
        required_keys = ["decisions", "power", "fear", "reward", "meaning"]
        for key in required_keys:
            if key not in v or not (0 <= v[key] <= 1):
                raise ValueError(f"Invalid confidence score for {key}")
        return v

class FourthOntologyEngine:
    """
    Engine for extracting and managing Fourth Ontology dimensions
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.2,
            openai_api_key=settings.OPENAI_API_KEY
        )
        self.parser = PydanticOutputParser(pydantic_object=OntologyExtraction)
        
        # Load dimension configurations
        self.dimensions_config = settings.ONTOLOGY_DIMENSIONS
        
        # Extraction prompt template
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert behavioral analyst specializing in the Fourth Ontology framework.
            Analyze the provided behavioral data and extract scores for each dimension on a 0-100 scale.
            
            The dimensions are:
            - DECISIONS: How much analysis/data is required before decisions (0=instant, 100=exhaustive analysis)
            - POWER: Comfort with autonomy and control (0=fully delegated, 100=complete control)
            - FEAR: Risk tolerance and safety needs (0=risk-seeking, 100=maximum safety)
            - REWARD: Response to incentives and achievements (0=intrinsic only, 100=highly extrinsic)
            - MEANING: Value alignment importance (0=task-focused, 100=purpose-driven)
            
            {format_instructions}
            """),
            ("human", """Analyze this behavioral data:
            
            Communication Patterns:
            {communication_data}
            
            Decision History:
            {decision_data}
            
            Task Execution Patterns:
            {task_data}
            
            Time-based Behaviors:
            {temporal_data}
            
            Extract Fourth Ontology dimensions with supporting patterns and confidence scores.""")
        ])
    
    def extract_ontology(
        self,
        persona_id: str,
        communication_data: List[Dict],
        decision_data: List[Dict],
        task_data: List[Dict],
        temporal_data: List[Dict]
    ) -> Dict[str, DimensionAnalysis]:
        """
        Extract Fourth Ontology dimensions from behavioral data
        """
        try:
            logger.info(f"Extracting ontology for persona {persona_id}")
            
            # Prepare data summaries
            comm_summary = self._summarize_communication(communication_data)
            decision_summary = self._summarize_decisions(decision_data)
            task_summary = self._summarize_tasks(task_data)
            temporal_summary = self._summarize_temporal(temporal_data)
            
            # Get LLM extraction
            prompt = self.extraction_prompt.format_prompt(
                format_instructions=self.parser.get_format_instructions(),
                communication_data=comm_summary,
                decision_data=decision_summary,
                task_data=task_summary,
                temporal_data=temporal_summary
            )
            
            response = self.llm.predict(prompt.to_string())
            extraction = self.parser.parse(response)
            
            # Build dimension analyses
            analyses = {}
            for dim in OntologyDimension:
                dim_name = dim.value
                analyses[dim_name] = DimensionAnalysis(
                    dimension=dim,
                    value=getattr(extraction, f"{dim_name}_value"),
                    confidence=extraction.confidence_scores[dim_name],
                    evidence_count=len(getattr(extraction, f"{dim_name}_patterns")),
                    patterns=getattr(extraction, f"{dim_name}_patterns"),
                    metadata=self._generate_metadata(dim, extraction)
                )
            
            # Store in database
            self._store_ontology(persona_id, analyses)
            
            # Extract negative space boundaries
            boundaries = self._extract_boundaries(persona_id, analyses)
            
            return analyses
            
        except Exception as e:
            logger.error(f"Ontology extraction failed: {str(e)}")
            raise
    
    def adjust_dimension(
        self,
        persona_id: str,
        dimension: OntologyDimension,
        new_value: float,
        reason: str
    ) -> bool:
        """
        Manually adjust a dimension value
        """
        try:
            with get_db() as db:
                ontology = db.query(OntologyMapping).filter(
                    OntologyMapping.persona_id == persona_id
                ).first()
                
                if not ontology:
                    logger.error(f"Ontology not found for persona {persona_id}")
                    return False
                
                # Store old value
                old_value = getattr(ontology, f"{dimension.value}_value")
                
                # Update value
                setattr(ontology, f"{dimension.value}_value", new_value)
                
                # Add to adjustment history
                if not ontology.adjustment_history:
                    ontology.adjustment_history = []
                
                ontology.adjustment_history.append({
                    "dimension": dimension.value,
                    "old_value": old_value,
                    "new_value": new_value,
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                ontology.updated_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"Adjusted {dimension.value} from {old_value} to {new_value} for persona {persona_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to adjust dimension: {str(e)}")
            return False
    
    def calculate_behavioral_distance(
        self,
        persona_id_1: str,
        persona_id_2: str
    ) -> float:
        """
        Calculate behavioral distance between two personas using Fourth Ontology
        """
        try:
            with get_db() as db:
                ontology1 = db.query(OntologyMapping).filter(
                    OntologyMapping.persona_id == persona_id_1
                ).first()
                
                ontology2 = db.query(OntologyMapping).filter(
                    OntologyMapping.persona_id == persona_id_2
                ).first()
                
                if not ontology1 or not ontology2:
                    raise ValueError("One or both personas not found")
                
                # Extract dimension values
                values1 = np.array([
                    ontology1.decisions_value,
                    ontology1.power_value,
                    ontology1.fear_value,
                    ontology1.reward_value,
                    ontology1.meaning_value
                ])
                
                values2 = np.array([
                    ontology2.decisions_value,
                    ontology2.power_value,
                    ontology2.fear_value,
                    ontology2.reward_value,
                    ontology2.meaning_value
                ])
                
                # Apply dimension weights
                weights = np.array([
                    self.dimensions_config["decisions"]["weight"],
                    self.dimensions_config["power"]["weight"],
                    self.dimensions_config["fear"]["weight"],
                    self.dimensions_config["reward"]["weight"],
                    self.dimensions_config["meaning"]["weight"]
                ])
                
                # Calculate weighted Euclidean distance
                distance = np.sqrt(np.sum(weights * (values1 - values2) ** 2))
                
                # Normalize to 0-1 scale
                max_distance = np.sqrt(np.sum(weights * (100 ** 2)))
                normalized_distance = distance / max_distance
                
                return normalized_distance
                
        except Exception as e:
            logger.error(f"Failed to calculate behavioral distance: {str(e)}")
            raise
    
    def get_delegation_recommendations(
        self,
        persona_id: str,
        task_type: str
    ) -> Dict[str, Any]:
        """
        Get task delegation recommendations based on Fourth Ontology
        """
        try:
            with get_db() as db:
                ontology = db.query(OntologyMapping).filter(
                    OntologyMapping.persona_id == persona_id
                ).first()
                
                if not ontology:
                    raise ValueError(f"Ontology not found for persona {persona_id}")
                
                recommendations = {
                    "can_delegate": True,
                    "confidence": 0.0,
                    "require_approval": False,
                    "risk_level": "low",
                    "adjustments_needed": [],
                    "guardrails": []
                }
                
                # Analyze based on task type
                if "financial" in task_type.lower() or "billing" in task_type.lower():
                    # High fear dimension suggests caution with financial tasks
                    if ontology.fear_value > 70:
                        recommendations["require_approval"] = True
                        recommendations["risk_level"] = "high"
                        recommendations["guardrails"].append("Require approval for all financial decisions")
                
                if "strategic" in task_type.lower() or "planning" in task_type.lower():
                    # High decisions dimension suggests deep analysis preference
                    if ontology.decisions_value > 80:
                        recommendations["adjustments_needed"].append(
                            "Provide comprehensive data analysis before execution"
                        )
                        recommendations["confidence"] = max(0, recommendations["confidence"] - 0.2)
                
                if "urgent" in task_type.lower() or "emergency" in task_type.lower():
                    # Low power dimension suggests discomfort with urgent autonomous action
                    if ontology.power_value < 30:
                        recommendations["require_approval"] = True
                        recommendations["guardrails"].append("Escalate all urgent decisions")
                
                # Calculate overall confidence
                base_confidence = 0.5
                confidence_modifiers = {
                    "decisions": abs(50 - ontology.decisions_value) / 100,
                    "power": abs(50 - ontology.power_value) / 100,
                    "fear": abs(50 - ontology.fear_value) / 100
                }
                
                recommendations["confidence"] = base_confidence + sum(confidence_modifiers.values()) / 3
                
                return recommendations
                
        except Exception as e:
            logger.error(f"Failed to get delegation recommendations: {str(e)}")
            return {
                "can_delegate": False,
                "confidence": 0.0,
                "require_approval": True,
                "risk_level": "unknown",
                "error": str(e)
            }
    
    def _summarize_communication(self, data: List[Dict]) -> str:
        """Summarize communication patterns for LLM analysis"""
        if not data:
            return "No communication data available"
        
        summary = []
        summary.append(f"Total communications analyzed: {len(data)}")
        
        # Response time analysis
        response_times = [d.get("response_time", 0) for d in data if d.get("response_time")]
        if response_times:
            avg_response = np.mean(response_times)
            summary.append(f"Average response time: {avg_response:.1f} minutes")
        
        # Message length analysis
        message_lengths = [d.get("message_length", 0) for d in data if d.get("message_length")]
        if message_lengths:
            avg_length = np.mean(message_lengths)
            summary.append(f"Average message length: {avg_length:.0f} characters")
        
        # Formality analysis
        formality_scores = [d.get("formality_score", 0.5) for d in data if d.get("formality_score")]
        if formality_scores:
            avg_formality = np.mean(formality_scores)
            summary.append(f"Formality level: {avg_formality:.2f} (0=casual, 1=formal)")
        
        return "\n".join(summary)
    
    def _summarize_decisions(self, data: List[Dict]) -> str:
        """Summarize decision patterns for LLM analysis"""
        if not data:
            return "No decision data available"
        
        summary = []
        summary.append(f"Total decisions analyzed: {len(data)}")
        
        # Decision speed
        decision_times = [d.get("time_to_decision", 0) for d in data if d.get("time_to_decision")]
        if decision_times:
            avg_time = np.mean(decision_times)
            summary.append(f"Average time to decision: {avg_time:.1f} hours")
        
        # Data requirements
        data_points = [d.get("data_points_used", 0) for d in data if d.get("data_points_used")]
        if data_points:
            avg_data = np.mean(data_points)
            summary.append(f"Average data points consulted: {avg_data:.1f}")
        
        # Collaboration
        solo_decisions = sum(1 for d in data if d.get("made_alone", False))
        summary.append(f"Solo decisions: {solo_decisions}/{len(data)} ({100*solo_decisions/len(data):.1f}%)")
        
        return "\n".join(summary)
    
    def _summarize_tasks(self, data: List[Dict]) -> str:
        """Summarize task execution patterns for LLM analysis"""
        if not data:
            return "No task data available"
        
        summary = []
        summary.append(f"Total tasks analyzed: {len(data)}")
        
        # Completion rate
        completed = sum(1 for d in data if d.get("completed", False))
        summary.append(f"Completion rate: {100*completed/len(data):.1f}%")
        
        # Delegation patterns
        delegated = sum(1 for d in data if d.get("delegated", False))
        summary.append(f"Delegation rate: {100*delegated/len(data):.1f}%")
        
        # Tool usage
        tools_used = set()
        for d in data:
            if d.get("tools_used"):
                tools_used.update(d["tools_used"])
        summary.append(f"Unique tools used: {len(tools_used)}")
        
        return "\n".join(summary)
    
    def _summarize_temporal(self, data: List[Dict]) -> str:
        """Summarize temporal patterns for LLM analysis"""
        if not data:
            return "No temporal data available"
        
        summary = []
        
        # Work hours distribution
        work_hours = [d.get("hour", 0) for d in data if d.get("hour") is not None]
        if work_hours:
            early_morning = sum(1 for h in work_hours if 5 <= h < 9)
            morning = sum(1 for h in work_hours if 9 <= h < 12)
            afternoon = sum(1 for h in work_hours if 12 <= h < 17)
            evening = sum(1 for h in work_hours if 17 <= h < 21)
            night = sum(1 for h in work_hours if h < 5 or h >= 21)
            
            total = len(work_hours)
            summary.append(f"Work distribution: Early morning {100*early_morning/total:.1f}%, "
                         f"Morning {100*morning/total:.1f}%, Afternoon {100*afternoon/total:.1f}%, "
                         f"Evening {100*evening/total:.1f}%, Night {100*night/total:.1f}%")
        
        # Weekend work
        weekend_work = sum(1 for d in data if d.get("is_weekend", False))
        summary.append(f"Weekend work: {100*weekend_work/len(data):.1f}%")
        
        return "\n".join(summary)
    
    def _generate_metadata(self, dimension: OntologyDimension, extraction: OntologyExtraction) -> Dict:
        """Generate metadata for a dimension"""
        return {
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "model_used": settings.OPENAI_MODEL,
            "patterns": getattr(extraction, f"{dimension.value}_patterns"),
            "confidence": extraction.confidence_scores[dimension.value]
        }
    
    def _store_ontology(self, persona_id: str, analyses: Dict[str, DimensionAnalysis]):
        """Store extracted ontology in database"""
        try:
            with get_db() as db:
                # Get or create ontology mapping
                ontology = db.query(OntologyMapping).filter(
                    OntologyMapping.persona_id == persona_id
                ).first()
                
                if not ontology:
                    ontology = OntologyMapping(persona_id=persona_id)
                    db.add(ontology)
                
                # Update dimension values
                for dim_name, analysis in analyses.items():
                    setattr(ontology, f"{dim_name}_value", analysis.value)
                    setattr(ontology, f"{dim_name}_confidence", analysis.confidence)
                    setattr(ontology, f"{dim_name}_evidence_count", analysis.evidence_count)
                    setattr(ontology, f"{dim_name}_metadata", analysis.metadata)
                
                ontology.last_calculated = datetime.utcnow()
                db.commit()
                
                logger.info(f"Stored ontology for persona {persona_id}")
                
        except Exception as e:
            logger.error(f"Failed to store ontology: {str(e)}")
            raise
    
    def _extract_boundaries(
        self,
        persona_id: str,
        analyses: Dict[str, DimensionAnalysis]
    ) -> List[NegativeSpaceBoundary]:
        """Extract negative space boundaries from ontology analysis"""
        boundaries = []
        
        try:
            with get_db() as db:
                # High fear score suggests risk-averse boundaries
                if analyses["fear"].value > 75:
                    boundary = NegativeSpaceBoundary(
                        persona_id=persona_id,
                        dimension="High-Risk Operations",
                        pattern="Avoids operations that could impact system stability",
                        evidence=f"Fear dimension score: {analyses['fear'].value}",
                        risk_level=BoundaryRiskLevel.HIGH,
                        is_guardrail=True,
                        category="Technical"
                    )
                    db.add(boundary)
                    boundaries.append(boundary)
                
                # Low power score suggests delegation boundaries
                if analyses["power"].value < 30:
                    boundary = NegativeSpaceBoundary(
                        persona_id=persona_id,
                        dimension="Autonomous Decision Making",
                        pattern="Rarely makes significant decisions without consultation",
                        evidence=f"Power dimension score: {analyses['power'].value}",
                        risk_level=BoundaryRiskLevel.MEDIUM,
                        is_guardrail=False,
                        category="Process"
                    )
                    db.add(boundary)
                    boundaries.append(boundary)
                
                # High decisions score suggests analysis boundaries
                if analyses["decisions"].value > 85:
                    boundary = NegativeSpaceBoundary(
                        persona_id=persona_id,
                        dimension="Quick Decision Requirements",
                        pattern="Avoids situations requiring immediate decisions without data",
                        evidence=f"Decisions dimension score: {analyses['decisions'].value}",
                        risk_level=BoundaryRiskLevel.LOW,
                        is_guardrail=False,
                        category="Process"
                    )
                    db.add(boundary)
                    boundaries.append(boundary)
                
                db.commit()
                logger.info(f"Extracted {len(boundaries)} boundaries for persona {persona_id}")
                
        except Exception as e:
            logger.error(f"Failed to extract boundaries: {str(e)}")
        
        return boundaries

# Export main engine class
__all__ = ["FourthOntologyEngine", "OntologyDimension", "DimensionAnalysis"]