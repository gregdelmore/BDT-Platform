"""
Decision Engine - Autonomous decision-making with Fourth Ontology integration
"""
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from datetime import datetime
import json
import logging
from dataclasses import dataclass
from enum import Enum

from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory

from ..config import settings
from ..database import (
    get_db, DelegatedTask, TaskStatus, OntologyMapping,
    NegativeSpaceBoundary, BehavioralPattern, Persona
)
from .ontology_engine import FourthOntologyEngine
from .negative_space import NegativeSpaceAnalyzer, BoundaryCheck

logger = logging.getLogger(__name__)

class DecisionType(str, Enum):
    """Types of decisions the agent can make"""
    ROUTINE = "routine"           # Standard, repeatable decisions
    ANALYTICAL = "analytical"     # Data-driven decisions
    CREATIVE = "creative"         # Novel problem solving
    STRATEGIC = "strategic"       # Long-term planning
    EMERGENCY = "emergency"       # Urgent response required

@dataclass
class DecisionContext:
    """Context for decision-making"""
    task: DelegatedTask
    ontology: OntologyMapping
    boundaries: List[NegativeSpaceBoundary]
    patterns: List[BehavioralPattern]
    historical_decisions: List[Dict]
    confidence_threshold: float
    risk_tolerance: float

@dataclass
class DecisionResult:
    """Result of autonomous decision"""
    decision: str
    confidence: float
    risk_score: float
    reasoning: List[str]
    requires_approval: bool
    suggested_actions: List[Dict]
    boundary_checks: List[BoundaryCheck]
    ontology_alignment: Dict[str, float]

class AutonomousDecisionEngine:
    """
    Engine for L4 autonomous decision-making with behavioral alignment
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.3,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        self.ontology_engine = FourthOntologyEngine()
        self.boundary_analyzer = NegativeSpaceAnalyzer()
        
        # Decision templates for different ontology profiles
        self.decision_templates = {
            "high_decisions": "Conduct thorough analysis with multiple data sources",
            "low_decisions": "Make quick decision based on available information",
            "high_power": "Take autonomous action within defined scope",
            "low_power": "Prepare recommendation for approval",
            "high_fear": "Implement multiple safety checks and validations",
            "low_fear": "Accept calculated risks for potential gains",
            "high_reward": "Optimize for measurable outcomes and KPIs",
            "low_reward": "Focus on intrinsic value and long-term impact",
            "high_meaning": "Align with organizational values and mission",
            "low_meaning": "Prioritize efficiency and task completion"
        }
        
        self.decision_prompt = ChatPromptTemplate.from_template("""
        You are acting as a digital twin with the following behavioral profile:
        
        Ontology Profile:
        - Decisions (Analysis Depth): {decisions_value}/100 - {decisions_desc}
        - Power (Autonomy): {power_value}/100 - {power_desc}
        - Fear (Risk Aversion): {fear_value}/100 - {fear_desc}
        - Reward (Motivation): {reward_value}/100 - {reward_desc}
        - Meaning (Value Alignment): {meaning_value}/100 - {meaning_desc}
        
        Task: {task_description}
        Task Type: {task_type}
        
        Historical Patterns:
        {patterns}
        
        Behavioral Boundaries (DO NOT VIOLATE):
        {boundaries}
        
        Context:
        {context}
        
        Based on this behavioral profile, make a decision that:
        1. Aligns with the ontology values
        2. Respects all boundaries
        3. Follows historical patterns
        4. Achieves the task objective
        
        Provide:
        1. Your decision
        2. Step-by-step reasoning
        3. Confidence level (0-1)
        4. Risk assessment
        5. Specific actions to take
        """)
    
    def make_decision(self, context: DecisionContext) -> DecisionResult:
        """
        Make an autonomous decision based on behavioral profile
        """
        logger.info(f"Making decision for task {context.task.id}")
        
        # Check boundaries first
        boundary_checks = self.boundary_analyzer.check_boundaries(
            context.task.persona_id,
            context.task,
            {"timestamp": datetime.utcnow()}
        )
        
        # If critical boundaries violated, don't proceed
        critical_violations = [
            check for check in boundary_checks
            if check.violated and check.severity > 0.8
        ]
        
        if critical_violations:
            return self._create_blocked_decision(critical_violations)
        
        # Calculate decision approach based on ontology
        approach = self._determine_approach(context.ontology)
        
        # Generate decision
        decision = self._generate_decision(context, approach, boundary_checks)
        
        # Validate decision alignment
        alignment = self._validate_alignment(decision, context.ontology)
        
        # Determine if approval needed
        requires_approval = self._requires_approval(
            decision,
            context.ontology,
            boundary_checks
        )
        
        return DecisionResult(
            decision=decision["decision"],
            confidence=decision["confidence"],
            risk_score=decision["risk_score"],
            reasoning=decision["reasoning"],
            requires_approval=requires_approval,
            suggested_actions=decision["actions"],
            boundary_checks=boundary_checks,
            ontology_alignment=alignment
        )
    
    def learn_from_outcome(
        self,
        task_id: str,
        outcome: Dict[str, Any],
        feedback: Optional[str] = None
    ) -> bool:
        """
        Learn from task execution outcome
        """
        try:
            with get_db() as db:
                task = db.query(DelegatedTask).filter(
                    DelegatedTask.id == task_id
                ).first()
                
                if not task:
                    return False
                
                # Extract learning points
                learning = self._extract_learning(task, outcome, feedback)
                
                # Update behavioral patterns
                self._update_patterns(task.persona_id, learning)
                
                # Adjust ontology if significant deviation
                if learning.get("ontology_adjustment"):
                    self._adjust_ontology(
                        task.persona_id,
                        learning["ontology_adjustment"]
                    )
                
                # Update boundaries if needed
                if learning.get("boundary_learning"):
                    self._update_boundaries(
                        task.persona_id,
                        learning["boundary_learning"]
                    )
                
                # Store learning in task
                task.patterns_learned = learning
                task.feedback_score = outcome.get("success_score", 0)
                task.feedback_notes = feedback
                
                db.commit()
                logger.info(f"Learning recorded for task {task_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to learn from outcome: {str(e)}")
            return False
    
    def simulate_decision(
        self,
        persona_id: str,
        task_description: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate a decision without executing (for testing/preview)
        """
        try:
            with get_db() as db:
                # Get persona data
                persona = db.query(Persona).filter(
                    Persona.id == persona_id
                ).first()
                
                if not persona:
                    raise ValueError(f"Persona {persona_id} not found")
                
                # Create simulated task
                simulated_task = DelegatedTask(
                    persona_id=persona_id,
                    task_type="simulation",
                    task_description=task_description,
                    input_data=context,
                    confidence_score=0,
                    risk_score=0
                )
                
                # Get ontology and patterns
                ontology = db.query(OntologyMapping).filter(
                    OntologyMapping.persona_id == persona_id
                ).first()
                
                boundaries = db.query(NegativeSpaceBoundary).filter(
                    NegativeSpaceBoundary.persona_id == persona_id,
                    NegativeSpaceBoundary.is_active == True
                ).all()
                
                patterns = db.query(BehavioralPattern).filter(
                    BehavioralPattern.persona_id == persona_id
                ).limit(10).all()
                
                # Create context
                decision_context = DecisionContext(
                    task=simulated_task,
                    ontology=ontology,
                    boundaries=boundaries,
                    patterns=patterns,
                    historical_decisions=[],
                    confidence_threshold=settings.HILT_CONFIDENCE_THRESHOLD,
                    risk_tolerance=1 - (ontology.fear_value / 100)
                )
                
                # Make simulated decision
                result = self.make_decision(decision_context)
                
                return {
                    "decision": result.decision,
                    "confidence": result.confidence,
                    "risk_score": result.risk_score,
                    "reasoning": result.reasoning,
                    "requires_approval": result.requires_approval,
                    "actions": result.suggested_actions,
                    "boundary_concerns": [
                        {
                            "boundary": check.boundary_id,
                            "violated": check.violated,
                            "severity": check.severity,
                            "recommendation": check.recommendation
                        }
                        for check in result.boundary_checks
                        if check.violated or check.distance_to_boundary < 0.3
                    ],
                    "ontology_alignment": result.ontology_alignment
                }
                
        except Exception as e:
            logger.error(f"Simulation failed: {str(e)}")
            return {
                "error": str(e),
                "decision": None,
                "requires_approval": True
            }
    
    def _determine_approach(self, ontology: OntologyMapping) -> Dict[str, str]:
        """Determine decision approach based on ontology"""
        approach = {
            "analysis_level": "",
            "autonomy_level": "",
            "risk_approach": "",
            "motivation_focus": "",
            "value_consideration": ""
        }
        
        # Analysis approach
        if ontology.decisions_value > 70:
            approach["analysis_level"] = self.decision_templates["high_decisions"]
        else:
            approach["analysis_level"] = self.decision_templates["low_decisions"]
        
        # Autonomy approach
        if ontology.power_value > 60:
            approach["autonomy_level"] = self.decision_templates["high_power"]
        else:
            approach["autonomy_level"] = self.decision_templates["low_power"]
        
        # Risk approach
        if ontology.fear_value > 70:
            approach["risk_approach"] = self.decision_templates["high_fear"]
        else:
            approach["risk_approach"] = self.decision_templates["low_fear"]
        
        # Motivation approach
        if ontology.reward_value > 60:
            approach["motivation_focus"] = self.decision_templates["high_reward"]
        else:
            approach["motivation_focus"] = self.decision_templates["low_reward"]
        
        # Value approach
        if ontology.meaning_value > 70:
            approach["value_consideration"] = self.decision_templates["high_meaning"]
        else:
            approach["value_consideration"] = self.decision_templates["low_meaning"]
        
        return approach
    
    def _generate_decision(
        self,
        context: DecisionContext,
        approach: Dict[str, str],
        boundary_checks: List[BoundaryCheck]
    ) -> Dict[str, Any]:
        """Generate the actual decision"""
        
        # Prepare patterns summary
        patterns_summary = self._summarize_patterns(context.patterns)
        
        # Prepare boundaries summary
        boundaries_summary = self._summarize_boundaries(
            context.boundaries,
            boundary_checks
        )
        
        # Generate decision using LLM
        prompt_values = {
            "decisions_value": context.ontology.decisions_value,
            "decisions_desc": approach["analysis_level"],
            "power_value": context.ontology.power_value,
            "power_desc": approach["autonomy_level"],
            "fear_value": context.ontology.fear_value,
            "fear_desc": approach["risk_approach"],
            "reward_value": context.ontology.reward_value,
            "reward_desc": approach["motivation_focus"],
            "meaning_value": context.ontology.meaning_value,
            "meaning_desc": approach["value_consideration"],
            "task_description": context.task.task_description,
            "task_type": context.task.task_type,
            "patterns": patterns_summary,
            "boundaries": boundaries_summary,
            "context": json.dumps(context.task.input_data)
        }
        
        response = self.llm.predict(
            self.decision_prompt.format(**prompt_values)
        )
        
        # Parse response
        decision_data = self._parse_decision_response(response)
        
        # Calculate confidence based on alignment
        confidence = self._calculate_confidence(
            decision_data,
            context.ontology,
            boundary_checks
        )
        
        # Calculate risk score
        risk_score = self._calculate_risk(
            decision_data,
            context.ontology,
            boundary_checks
        )
        
        decision_data["confidence"] = confidence
        decision_data["risk_score"] = risk_score
        
        return decision_data
    
    def _validate_alignment(
        self,
        decision: Dict[str, Any],
        ontology: OntologyMapping
    ) -> Dict[str, float]:
        """Validate decision alignment with ontology"""
        alignment = {}
        
        # Check decisions dimension alignment
        if "analysis" in str(decision).lower():
            analysis_depth = len(decision.get("reasoning", []))
            expected_depth = ontology.decisions_value / 10
            alignment["decisions"] = 1 - abs(analysis_depth - expected_depth) / 10
        else:
            alignment["decisions"] = 0.5
        
        # Check power dimension alignment
        if decision.get("requires_approval"):
            alignment["power"] = 1 - (ontology.power_value / 100)
        else:
            alignment["power"] = ontology.power_value / 100
        
        # Check fear dimension alignment
        risk_score = decision.get("risk_score", 0.5)
        expected_risk_tolerance = 1 - (ontology.fear_value / 100)
        alignment["fear"] = 1 - abs(risk_score - expected_risk_tolerance)
        
        # Check reward dimension alignment
        if any(word in str(decision).lower() 
               for word in ["metric", "kpi", "measure", "achievement"]):
            alignment["reward"] = ontology.reward_value / 100
        else:
            alignment["reward"] = 1 - (ontology.reward_value / 100)
        
        # Check meaning dimension alignment
        if any(word in str(decision).lower()
               for word in ["value", "mission", "purpose", "principle"]):
            alignment["meaning"] = ontology.meaning_value / 100
        else:
            alignment["meaning"] = 1 - (ontology.meaning_value / 100)
        
        return alignment
    
    def _requires_approval(
        self,
        decision: Dict[str, Any],
        ontology: OntologyMapping,
        boundary_checks: List[BoundaryCheck]
    ) -> bool:
        """Determine if decision requires human approval"""
        
        # Check confidence threshold
        if decision["confidence"] < settings.HILT_CONFIDENCE_THRESHOLD:
            return True
        
        # Check risk threshold
        if decision["risk_score"] > settings.HILT_RISK_THRESHOLD:
            return True
        
        # Check boundary violations
        if any(check.violated for check in boundary_checks):
            return True
        
        # Check ontology-based approval needs
        if ontology.power_value < 30:  # Low autonomy preference
            return True
        
        if ontology.fear_value > 80:  # High risk aversion
            if decision["risk_score"] > 0.3:
                return True
        
        # Check for specific keywords requiring approval
        approval_keywords = [
            "financial", "budget", "payment", "contract",
            "customer", "client", "executive", "legal",
            "production", "security", "compliance"
        ]
        
        decision_text = str(decision).lower()
        if any(keyword in decision_text for keyword in approval_keywords):
            return True
        
        return False
    
    def _create_blocked_decision(
        self,
        violations: List[BoundaryCheck]
    ) -> DecisionResult:
        """Create a blocked decision due to boundary violations"""
        return DecisionResult(
            decision="BLOCKED: Critical boundary violation detected",
            confidence=0.0,
            risk_score=1.0,
            reasoning=[
                f"Violation: {v.recommendation}" for v in violations
            ],
            requires_approval=True,
            suggested_actions=[
                {
                    "action": "escalate",
                    "description": "Escalate to human for override or alternative approach"
                }
            ],
            boundary_checks=violations,
            ontology_alignment={}
        )
    
    def _summarize_patterns(self, patterns: List[BehavioralPattern]) -> str:
        """Summarize behavioral patterns for decision context"""
        if not patterns:
            return "No historical patterns available"
        
        summary = []
        for pattern in patterns[:5]:  # Top 5 most relevant
            summary.append(
                f"- {pattern.pattern_name}: {pattern.pattern_description} "
                f"(confidence: {pattern.confidence:.2f})"
            )
        
        return "\n".join(summary)
    
    def _summarize_boundaries(
        self,
        boundaries: List[NegativeSpaceBoundary],
        checks: List[BoundaryCheck]
    ) -> str:
        """Summarize boundaries for decision context"""
        summary = []
        
        # Active guardrails
        guardrails = [b for b in boundaries if b.is_guardrail]
        if guardrails:
            summary.append(f"CRITICAL GUARDRAILS ({len(guardrails)}):")
            for g in guardrails[:3]:
                summary.append(f"- {g.dimension}: {g.pattern}")
        
        # Violations detected
        violations = [c for c in checks if c.violated]
        if violations:
            summary.append(f"\nVIOLATIONS DETECTED ({len(violations)}):")
            for v in violations:
                summary.append(f"- {v.recommendation}")
        
        # Near misses
        near_misses = [c for c in checks if not c.violated and c.distance_to_boundary < 0.3]
        if near_misses:
            summary.append(f"\nNEAR BOUNDARIES ({len(near_misses)}):")
            for n in near_misses:
                summary.append(f"- Distance: {n.distance_to_boundary:.2f}")
        
        return "\n".join(summary) if summary else "No boundary concerns"
    
    def _parse_decision_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured decision"""
        # This is a simplified parser - in production, use structured output
        lines = response.strip().split("\n")
        
        decision_data = {
            "decision": "",
            "reasoning": [],
            "actions": []
        }
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if "decision:" in line.lower():
                current_section = "decision"
                decision_data["decision"] = line.split(":", 1)[1].strip()
            elif "reasoning:" in line.lower() or "step" in line.lower():
                current_section = "reasoning"
                if ":" in line:
                    decision_data["reasoning"].append(line.split(":", 1)[1].strip())
            elif "action" in line.lower():
                current_section = "actions"
                if ":" in line:
                    action_text = line.split(":", 1)[1].strip()
                    decision_data["actions"].append({
                        "action": "execute",
                        "description": action_text
                    })
            elif current_section == "reasoning":
                decision_data["reasoning"].append(line)
            elif current_section == "actions":
                decision_data["actions"].append({
                    "action": "execute",
                    "description": line
                })
        
        return decision_data
    
    def _calculate_confidence(
        self,
        decision: Dict[str, Any],
        ontology: OntologyMapping,
        boundary_checks: List[BoundaryCheck]
    ) -> float:
        """Calculate confidence score for decision"""
        base_confidence = 0.5
        
        # Adjust based on reasoning depth
        reasoning_count = len(decision.get("reasoning", []))
        if ontology.decisions_value > 70:  # High analysis preference
            if reasoning_count >= 5:
                base_confidence += 0.2
            else:
                base_confidence -= 0.1
        else:  # Low analysis preference
            if reasoning_count <= 3:
                base_confidence += 0.1
        
        # Adjust based on boundary compliance
        violations = sum(1 for c in boundary_checks if c.violated)
        if violations == 0:
            base_confidence += 0.2
        else:
            base_confidence -= violations * 0.1
        
        # Adjust based on action clarity
        if decision.get("actions"):
            base_confidence += 0.1
        
        return max(0, min(1, base_confidence))
    
    def _calculate_risk(
        self,
        decision: Dict[str, Any],
        ontology: OntologyMapping,
        boundary_checks: List[BoundaryCheck]
    ) -> float:
        """Calculate risk score for decision"""
        base_risk = 0.3
        
        # Adjust based on boundary violations
        max_severity = max(
            [c.severity for c in boundary_checks if c.violated],
            default=0
        )
        base_risk += max_severity * 0.3
        
        # Adjust based on decision type
        decision_text = decision.get("decision", "").lower()
        high_risk_keywords = [
            "delete", "remove", "production", "customer",
            "financial", "contract", "legal", "security"
        ]
        
        for keyword in high_risk_keywords:
            if keyword in decision_text:
                base_risk += 0.1
        
        # Adjust based on ontology fear dimension
        fear_adjustment = ontology.fear_value / 100 * 0.2
        base_risk += fear_adjustment
        
        return max(0, min(1, base_risk))
    
    def _extract_learning(
        self,
        task: DelegatedTask,
        outcome: Dict[str, Any],
        feedback: Optional[str]
    ) -> Dict[str, Any]:
        """Extract learning points from task outcome"""
        learning = {
            "task_type": task.task_type,
            "success": outcome.get("success", False),
            "confidence_accuracy": None,
            "risk_accuracy": None,
            "patterns_observed": [],
            "boundary_learning": [],
            "ontology_adjustment": None
        }
        
        # Check confidence accuracy
        if task.confidence_score and "actual_difficulty" in outcome:
            predicted_confidence = task.confidence_score
            actual_success = 1 if outcome["success"] else 0
            learning["confidence_accuracy"] = 1 - abs(predicted_confidence - actual_success)
        
        # Check risk accuracy
        if task.risk_score and "actual_risk" in outcome:
            learning["risk_accuracy"] = 1 - abs(task.risk_score - outcome["actual_risk"])
        
        # Extract new patterns
        if feedback:
            # Simple pattern extraction from feedback
            if "always" in feedback.lower():
                learning["patterns_observed"].append({
                    "type": "consistent",
                    "description": feedback
                })
            if "never" in feedback.lower():
                learning["patterns_observed"].append({
                    "type": "boundary",
                    "description": feedback
                })
        
        # Check for boundary adjustments
        if outcome.get("boundary_feedback"):
            learning["boundary_learning"] = outcome["boundary_feedback"]
        
        # Check for ontology adjustments
        if outcome.get("behavioral_mismatch"):
            learning["ontology_adjustment"] = outcome["behavioral_mismatch"]
        
        return learning
    
    def _update_patterns(self, persona_id: str, learning: Dict[str, Any]):
        """Update behavioral patterns based on learning"""
        try:
            with get_db() as db:
                for pattern_data in learning.get("patterns_observed", []):
                    # Check if similar pattern exists
                    existing = db.query(BehavioralPattern).filter(
                        BehavioralPattern.persona_id == persona_id,
                        BehavioralPattern.pattern_name.like(
                            f"%{pattern_data['description'][:20]}%"
                        )
                    ).first()
                    
                    if existing:
                        existing.occurrence_count += 1
                        existing.confidence = min(
                            1.0,
                            existing.confidence + settings.AGENT_LEARNING_RATE
                        )
                        existing.last_observed = datetime.utcnow()
                    else:
                        new_pattern = BehavioralPattern(
                            persona_id=persona_id,
                            category="learned",
                            pattern_name=f"Learned: {pattern_data['description'][:50]}",
                            pattern_description=pattern_data["description"],
                            occurrence_count=1,
                            confidence=0.3,
                            strength=0.5
                        )
                        db.add(new_pattern)
                
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to update patterns: {str(e)}")
    
    def _adjust_ontology(self, persona_id: str, adjustment: Dict[str, Any]):
        """Adjust ontology based on learning"""
        try:
            for dimension, change in adjustment.items():
                if dimension in ["decisions", "power", "fear", "reward", "meaning"]:
                    self.ontology_engine.adjust_dimension(
                        persona_id,
                        dimension,
                        change["new_value"],
                        f"Learning adjustment: {change.get('reason', 'Behavioral observation')}"
                    )
        except Exception as e:
            logger.error(f"Failed to adjust ontology: {str(e)}")
    
    def _update_boundaries(self, persona_id: str, boundary_learning: List[Dict]):
        """Update boundaries based on learning"""
        try:
            for learning in boundary_learning:
                boundary_id = learning.get("boundary_id")
                if boundary_id:
                    self.boundary_analyzer.update_boundary_confidence(
                        boundary_id,
                        learning.get("feedback", ""),
                        learning.get("confidence_adjustment", 0)
                    )
        except Exception as e:
            logger.error(f"Failed to update boundaries: {str(e)}")

# Export main engine class
__all__ = ["AutonomousDecisionEngine", "DecisionType", "DecisionContext", "DecisionResult"]