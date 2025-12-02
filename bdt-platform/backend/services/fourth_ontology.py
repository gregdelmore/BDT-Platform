"""
Fourth Ontology Extraction Service
Manages the 5 behavioral dimensions: Decision, Power, Fear, Reward, Meaning
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime
import json
import asyncio
import openai

from core.config import settings
from core.models import PersonaModel, OntologyAdjustment, BehavioralPattern
from core.database import get_db_session

class FourthOntologyExtractor:
    """
    Extracts and manages the Fourth Ontology behavioral dimensions.
    This is the core differentiator of the BDT platform.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.client = openai.Client(api_key=settings.OPENAI_API_KEY)
        
        # Dimension definitions with analysis prompts
        self.dimensions = {
            "decision": {
                "name": "Decision Making",
                "description": "Analytical depth and data requirements for decisions",
                "scale": "0=Intuitive/Quick, 100=Highly Analytical/Data-driven",
                "indicators": [
                    "response_time_to_decisions",
                    "data_requests_before_approval",
                    "meeting_length_patterns",
                    "documentation_depth"
                ]
            },
            "power": {
                "name": "Autonomy & Control",
                "description": "Level of autonomous action vs approval seeking",
                "scale": "0=Seeks approval, 100=Fully autonomous",
                "indicators": [
                    "delegation_frequency",
                    "escalation_patterns",
                    "solo_decision_count",
                    "approval_request_frequency"
                ]
            },
            "fear": {
                "name": "Risk Tolerance",
                "description": "Comfort with risk and uncertainty",
                "scale": "0=Risk-taking, 100=Highly risk-averse",
                "indicators": [
                    "safety_language_frequency",
                    "verification_loops",
                    "backup_plan_mentions",
                    "cautionary_phrase_usage"
                ]
            },
            "reward": {
                "name": "Motivation Patterns",
                "description": "What drives action and satisfaction",
                "scale": "0=Intrinsic motivation, 100=External recognition",
                "indicators": [
                    "achievement_language",
                    "feedback_seeking_frequency",
                    "recognition_mentions",
                    "success_metric_references"
                ]
            },
            "meaning": {
                "name": "Value Alignment",
                "description": "Focus on purpose and strategic alignment",
                "scale": "0=Tactical focus, 100=Strategic/values-driven",
                "indicators": [
                    "mission_references",
                    "long_term_planning_language",
                    "value_statement_frequency",
                    "strategic_alignment_checks"
                ]
            }
        }
        
        # Source-specific weights for dimension extraction
        self.source_weights = {
            "email": {
                "decision": 0.3,
                "power": 0.2,
                "fear": 0.2,
                "reward": 0.2,
                "meaning": 0.1
            },
            "calendar": {
                "decision": 0.2,
                "power": 0.3,
                "fear": 0.1,
                "reward": 0.2,
                "meaning": 0.2
            },
            "documents": {
                "decision": 0.3,
                "power": 0.1,
                "fear": 0.3,
                "reward": 0.1,
                "meaning": 0.2
            },
            "chat": {
                "decision": 0.2,
                "power": 0.2,
                "fear": 0.1,
                "reward": 0.3,
                "meaning": 0.2
            }
        }
    
    async def extract_dimensions(
        self, 
        persona_id: int, 
        data_batch: Dict[str, List[Dict]]
    ) -> Dict[str, Any]:
        """
        Extract Fourth Ontology dimensions from a batch of data
        
        Args:
            persona_id: ID of the persona to analyze
            data_batch: Dictionary of data sources and their documents
            
        Returns:
            Dictionary with dimension scores and analysis details
        """
        
        persona = self.db.query(PersonaModel).filter_by(id=persona_id).first()
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")
        
        # Initialize dimension scores
        dimension_scores = {dim: [] for dim in self.dimensions.keys()}
        evidence_map = {dim: [] for dim in self.dimensions.keys()}
        
        # Process each data source
        for source_type, documents in data_batch.items():
            if not documents or source_type not in self.source_weights:
                continue
            
            # Analyze documents for this source
            source_analysis = await self._analyze_source(
                documents, 
                source_type
            )
            
            # Apply weighted scoring
            for dim, score in source_analysis["scores"].items():
                weight = self.source_weights[source_type].get(dim, 0.1)
                dimension_scores[dim].append(score * weight)
                evidence_map[dim].extend(source_analysis["evidence"].get(dim, []))
        
        # Calculate final scores
        final_scores = {}
        for dim in self.dimensions.keys():
            if dimension_scores[dim]:
                # Weighted average
                final_scores[dim] = np.mean(dimension_scores[dim])
            else:
                # Use current score if no new data
                final_scores[dim] = getattr(persona, f"{dim}_score", 0.5)
        
        # Update persona model
        for dim, score in final_scores.items():
            setattr(persona, f"{dim}_score", score)
        
        # Store behavioral patterns
        await self._store_patterns(persona_id, evidence_map)
        
        # Create analysis summary
        analysis_summary = self._create_analysis_summary(
            final_scores, 
            evidence_map
        )
        
        self.db.commit()
        
        return {
            "persona_id": persona_id,
            "dimensions": {
                dim: {
                    "score": final_scores[dim] * 100,  # Convert to 0-100 scale
                    "name": self.dimensions[dim]["name"],
                    "description": self.dimensions[dim]["description"],
                    "evidence_count": len(evidence_map[dim]),
                    "confidence": self._calculate_confidence(evidence_map[dim])
                }
                for dim in self.dimensions.keys()
            },
            "summary": analysis_summary,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _analyze_source(
        self, 
        documents: List[Dict], 
        source_type: str
    ) -> Dict[str, Any]:
        """
        Analyze documents from a specific source for behavioral patterns
        """
        
        # Prepare analysis context
        context = self._prepare_context(documents, source_type)
        
        # Use GPT-4 for behavioral analysis
        prompt = self._create_analysis_prompt(context, source_type)
        
        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert behavioral analyst specializing in the Fourth Ontology framework. Analyze the provided data for behavioral patterns across five dimensions: Decision, Power, Fear, Reward, and Meaning."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            # Validate and normalize scores
            scores = {}
            for dim in self.dimensions.keys():
                score = analysis.get("scores", {}).get(dim, 0.5)
                scores[dim] = max(0.0, min(1.0, score))
            
            return {
                "scores": scores,
                "evidence": analysis.get("evidence", {}),
                "patterns": analysis.get("patterns", {})
            }
            
        except Exception as e:
            # Fallback to rule-based analysis
            return self._fallback_analysis(documents, source_type)
    
    def _prepare_context(
        self, 
        documents: List[Dict], 
        source_type: str
    ) -> str:
        """
        Prepare document context for analysis
        """
        
        context_items = []
        
        if source_type == "email":
            for doc in documents[:50]:  # Limit to recent 50
                context_items.append({
                    "type": "email",
                    "sender": doc.get("sender", ""),
                    "recipients": doc.get("recipients", []),
                    "subject": doc.get("subject", ""),
                    "response_time": doc.get("response_time_minutes"),
                    "key_phrases": self._extract_key_phrases(doc.get("content", ""))
                })
                
        elif source_type == "calendar":
            for doc in documents[:50]:
                context_items.append({
                    "type": "meeting",
                    "title": doc.get("subject", ""),
                    "duration": doc.get("duration_minutes", 0),
                    "attendees": len(doc.get("attendees", [])),
                    "recurring": doc.get("is_recurring", False),
                    "time_slot": self._categorize_time_slot(doc.get("start_time"))
                })
                
        elif source_type == "documents":
            for doc in documents[:20]:
                context_items.append({
                    "type": "document",
                    "title": doc.get("title", ""),
                    "content_preview": doc.get("content", "")[:500],
                    "metadata": doc.get("metadata", {})
                })
                
        elif source_type == "chat":
            for doc in documents[:100]:
                context_items.append({
                    "type": "chat",
                    "message": doc.get("content", ""),
                    "timestamp": doc.get("timestamp", ""),
                    "channel": doc.get("channel", ""),
                    "participants": doc.get("participants", [])
                })
        
        return json.dumps(context_items, indent=2)
    
    def _create_analysis_prompt(
        self, 
        context: str, 
        source_type: str
    ) -> str:
        """
        Create analysis prompt for GPT-4
        """
        
        return f"""
        Analyze the following {source_type} data for behavioral patterns across the Fourth Ontology dimensions.
        
        Data:
        {context}
        
        For each dimension, provide:
        1. A score between 0.0 and 1.0
        2. Specific evidence from the data
        3. Identified patterns
        
        Dimensions to analyze:
        - DECISION: Analytical vs intuitive decision-making (0=intuitive, 1=analytical)
        - POWER: Autonomy level (0=seeks approval, 1=autonomous)
        - FEAR: Risk tolerance (0=risk-taking, 1=risk-averse)
        - REWARD: Motivation type (0=intrinsic, 1=external)
        - MEANING: Strategic focus (0=tactical, 1=strategic)
        
        Return JSON with structure:
        {{
            "scores": {{
                "decision": 0.0-1.0,
                "power": 0.0-1.0,
                "fear": 0.0-1.0,
                "reward": 0.0-1.0,
                "meaning": 0.0-1.0
            }},
            "evidence": {{
                "decision": ["evidence1", "evidence2"],
                "power": ["evidence1", "evidence2"],
                ...
            }},
            "patterns": {{
                "decision": "pattern description",
                "power": "pattern description",
                ...
            }}
        }}
        """
    
    def _fallback_analysis(
        self, 
        documents: List[Dict], 
        source_type: str
    ) -> Dict[str, Any]:
        """
        Rule-based fallback analysis when GPT-4 is unavailable
        """
        
        scores = {
            "decision": 0.5,
            "power": 0.5,
            "fear": 0.5,
            "reward": 0.5,
            "meaning": 0.5
        }
        
        evidence = {dim: [] for dim in scores.keys()}
        
        # Simple rule-based analysis
        for doc in documents[:20]:
            content = str(doc.get("content", "")).lower()
            
            # Decision dimension
            if any(word in content for word in ["analyze", "data", "research", "investigate"]):
                scores["decision"] += 0.02
                evidence["decision"].append("Analytical language detected")
            
            # Power dimension
            if any(word in content for word in ["approve", "authorize", "decide"]):
                scores["power"] += 0.02
                evidence["power"].append("Decision-making language detected")
            
            # Fear dimension
            if any(word in content for word in ["risk", "concern", "careful", "safety"]):
                scores["fear"] += 0.02
                evidence["fear"].append("Risk-awareness language detected")
            
            # Reward dimension
            if any(word in content for word in ["achievement", "success", "recognition"]):
                scores["reward"] += 0.02
                evidence["reward"].append("Achievement language detected")
            
            # Meaning dimension
            if any(word in content for word in ["mission", "vision", "strategy", "purpose"]):
                scores["meaning"] += 0.02
                evidence["meaning"].append("Strategic language detected")
        
        # Normalize scores
        for dim in scores.keys():
            scores[dim] = min(1.0, max(0.0, scores[dim]))
        
        return {
            "scores": scores,
            "evidence": evidence,
            "patterns": {dim: "Pattern detected via rule-based analysis" for dim in scores.keys()}
        }
    
    async def _store_patterns(
        self, 
        persona_id: int, 
        evidence_map: Dict[str, List]
    ):
        """
        Store extracted behavioral patterns in database
        """
        
        for dim, evidence_list in evidence_map.items():
            if not evidence_list:
                continue
            
            # Check for existing pattern
            pattern = self.db.query(BehavioralPattern).filter_by(
                persona_id=persona_id,
                pattern_type="fourth_ontology",
                pattern_name=dim
            ).first()
            
            if pattern:
                # Update existing pattern
                pattern.evidence_count += len(evidence_list)
                pattern.last_observed = datetime.utcnow()
                pattern.pattern_value = {
                    "evidence": evidence_list[-10:],  # Keep last 10 pieces of evidence
                    "total_count": pattern.evidence_count
                }
            else:
                # Create new pattern
                pattern = BehavioralPattern(
                    persona_id=persona_id,
                    pattern_type="fourth_ontology",
                    pattern_name=dim,
                    pattern_value={
                        "evidence": evidence_list[:10],
                        "total_count": len(evidence_list)
                    },
                    evidence_count=len(evidence_list),
                    confidence=self._calculate_confidence(evidence_list)
                )
                self.db.add(pattern)
    
    def _calculate_confidence(self, evidence_list: List) -> float:
        """
        Calculate confidence score based on evidence
        """
        
        if not evidence_list:
            return 0.0
        
        # More evidence = higher confidence, with diminishing returns
        base_confidence = min(0.5 + (len(evidence_list) * 0.05), 0.95)
        return base_confidence
    
    def _create_analysis_summary(
        self, 
        scores: Dict[str, float], 
        evidence_map: Dict[str, List]
    ) -> str:
        """
        Create human-readable analysis summary
        """
        
        # Find dominant dimensions
        sorted_dims = sorted(scores.items(), key=lambda x: abs(x[1] - 0.5), reverse=True)
        
        summary_parts = []
        
        for dim, score in sorted_dims[:3]:  # Top 3 most distinctive dimensions
            dim_info = self.dimensions[dim]
            
            if score > 0.7:
                level = "High"
                interpretation = dim_info["scale"].split(",")[1].strip()
            elif score < 0.3:
                level = "Low"
                interpretation = dim_info["scale"].split(",")[0].strip()
            else:
                level = "Moderate"
                interpretation = "Balanced approach"
            
            summary_parts.append(
                f"{dim_info['name']}: {level} ({score*100:.0f}%) - {interpretation}"
            )
        
        return " | ".join(summary_parts)
    
    async def adjust_dimension(
        self,
        persona_id: int,
        dimension: str,
        new_value: float,
        adjusted_by: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Manually adjust a Fourth Ontology dimension
        """
        
        if dimension not in self.dimensions:
            raise ValueError(f"Invalid dimension: {dimension}")
        
        if not 0 <= new_value <= 1:
            raise ValueError("Value must be between 0 and 1")
        
        persona = self.db.query(PersonaModel).filter_by(id=persona_id).first()
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")
        
        # Get current value
        current_value = getattr(persona, f"{dimension}_score")
        delta = new_value - current_value
        
        # Analyze impact
        impact_analysis = await self._analyze_adjustment_impact(
            persona, 
            dimension, 
            current_value, 
            new_value
        )
        
        # Create adjustment record
        adjustment = OntologyAdjustment(
            persona_id=persona_id,
            dimension=dimension,
            previous_value=current_value,
            new_value=new_value,
            delta=delta,
            adjustment_reason=reason,
            adjusted_by=adjusted_by,
            affected_boundaries=impact_analysis["affected_boundaries"],
            projected_impact=impact_analysis["behavioral_changes"]
        )
        self.db.add(adjustment)
        
        # Update persona
        setattr(persona, f"{dimension}_score", new_value)
        persona.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "adjustment_id": adjustment.id,
            "persona_id": persona_id,
            "dimension": dimension,
            "previous_value": current_value * 100,
            "new_value": new_value * 100,
            "delta": delta * 100,
            "impact_analysis": impact_analysis,
            "adjusted_by": adjusted_by,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _analyze_adjustment_impact(
        self,
        persona: PersonaModel,
        dimension: str,
        old_value: float,
        new_value: float
    ) -> Dict[str, List]:
        """
        Analyze the impact of adjusting an ontology dimension
        """
        
        delta = new_value - old_value
        impact = {
            "affected_boundaries": [],
            "behavioral_changes": []
        }
        
        # Dimension-specific impact analysis
        if dimension == "decision":
            if delta > 0:
                impact["behavioral_changes"].append("Will require more data before decisions")
                impact["behavioral_changes"].append("Longer analysis phase expected")
                impact["affected_boundaries"].append({
                    "type": "time",
                    "change": "Extended decision timelines"
                })
            else:
                impact["behavioral_changes"].append("Faster, more intuitive decisions")
                impact["behavioral_changes"].append("Reduced documentation requirements")
        
        elif dimension == "power":
            if delta > 0:
                impact["behavioral_changes"].append("Less escalation to management")
                impact["behavioral_changes"].append("Broader autonomous action scope")
                impact["affected_boundaries"].append({
                    "type": "decisions",
                    "change": "Expanded approval authority"
                })
            else:
                impact["behavioral_changes"].append("More collaborative decision-making")
                impact["behavioral_changes"].append("Increased checkpoint requirements")
        
        elif dimension == "fear":
            if delta > 0:
                impact["behavioral_changes"].append("More conservative approach to new initiatives")
                impact["behavioral_changes"].append("Additional verification steps")
                impact["affected_boundaries"].append({
                    "type": "tools",
                    "change": "Restricted to proven solutions"
                })
            else:
                impact["behavioral_changes"].append("Openness to experimental approaches")
                impact["behavioral_changes"].append("Reduced safety margins")
        
        elif dimension == "reward":
            if delta > 0:
                impact["behavioral_changes"].append("Increased focus on measurable outcomes")
                impact["behavioral_changes"].append("More frequent progress reporting")
            else:
                impact["behavioral_changes"].append("Greater emphasis on process quality")
                impact["behavioral_changes"].append("Less concern with external recognition")
        
        elif dimension == "meaning":
            if delta > 0:
                impact["behavioral_changes"].append("Prioritization of strategic initiatives")
                impact["behavioral_changes"].append("More alignment checks with mission")
                impact["affected_boundaries"].append({
                    "type": "tasks",
                    "change": "Focus on high-impact activities"
                })
            else:
                impact["behavioral_changes"].append("Increased attention to operational details")
                impact["behavioral_changes"].append("More tactical decision-making")
        
        return impact
    
    def get_current_scores(self, persona_id: int) -> Dict[str, Any]:
        """
        Get current Fourth Ontology scores for a persona
        """
        
        persona = self.db.query(PersonaModel).filter_by(id=persona_id).first()
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")
        
        return {
            "persona_id": persona_id,
            "dimensions": {
                dim: {
                    "score": getattr(persona, f"{dim}_score") * 100,
                    "name": self.dimensions[dim]["name"],
                    "description": self.dimensions[dim]["description"],
                    "scale": self.dimensions[dim]["scale"]
                }
                for dim in self.dimensions.keys()
            },
            "capability_level": persona.capability_level.value,
            "last_updated": persona.updated_at.isoformat() if persona.updated_at else None
        }
    
    def get_adjustment_history(
        self, 
        persona_id: int, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get history of ontology adjustments for a persona
        """
        
        adjustments = (
            self.db.query(OntologyAdjustment)
            .filter_by(persona_id=persona_id)
            .order_by(OntologyAdjustment.adjusted_at.desc())
            .limit(limit)
            .all()
        )
        
        return [
            {
                "adjustment_id": adj.id,
                "dimension": adj.dimension,
                "dimension_name": self.dimensions[adj.dimension]["name"],
                "previous_value": adj.previous_value * 100,
                "new_value": adj.new_value * 100,
                "delta": adj.delta * 100,
                "reason": adj.adjustment_reason,
                "adjusted_by": adj.adjusted_by,
                "adjusted_at": adj.adjusted_at.isoformat(),
                "impact": adj.projected_impact,
                "validated": adj.validated
            }
            for adj in adjustments
        ]
    
    def _extract_key_phrases(self, content: str) -> List[str]:
        """
        Extract key phrases from content
        """
        
        # Simple keyword extraction
        keywords = []
        
        # Decision indicators
        if any(word in content.lower() for word in ["analyze", "research", "investigate"]):
            keywords.append("analytical")
        
        # Power indicators
        if any(word in content.lower() for word in ["approve", "authorize", "delegate"]):
            keywords.append("authority")
        
        # Fear indicators
        if any(word in content.lower() for word in ["risk", "concern", "safety"]):
            keywords.append("risk-aware")
        
        # Reward indicators
        if any(word in content.lower() for word in ["achievement", "success", "recognition"]):
            keywords.append("achievement-focused")
        
        # Meaning indicators
        if any(word in content.lower() for word in ["mission", "vision", "strategy"]):
            keywords.append("strategic")
        
        return keywords
    
    def _categorize_time_slot(self, start_time: str) -> str:
        """
        Categorize meeting time slot
        """
        
        if not start_time:
            return "unknown"
        
        try:
            hour = datetime.fromisoformat(start_time).hour
            
            if hour < 9:
                return "early_morning"
            elif hour < 12:
                return "morning"
            elif hour < 14:
                return "lunch"
            elif hour < 17:
                return "afternoon"
            elif hour < 19:
                return "late_afternoon"
            else:
                return "evening"
        except:
            return "unknown"
