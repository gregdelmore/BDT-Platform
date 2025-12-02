"""
Risk Assessment Engine
Evaluates risk levels for proposed actions using multi-factor analysis
"""

from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import numpy as np

from core.config import settings
from core.models import RiskLevel, PersonaModel, HILTAction

class RiskAssessmentEngine:
    """
    Multi-factor risk assessment for HILT actions.
    Critical for determining auto-approval eligibility.
    """
    
    def __init__(self):
        # Risk factors and their weights
        self.risk_factors = {
            "financial_impact": 0.25,
            "data_sensitivity": 0.20,
            "reversibility": 0.15,
            "scope_of_impact": 0.15,
            "regulatory_compliance": 0.10,
            "pattern_deviation": 0.10,
            "time_criticality": 0.05
        }
        
        # Risk level thresholds
        self.thresholds = {
            "low": settings.RISK_MEDIUM_THRESHOLD,
            "medium": settings.RISK_HIGH_THRESHOLD,
            "high": settings.RISK_CRITICAL_THRESHOLD,
            "critical": 0.95
        }
    
    async def assess_action_risk(
        self,
        action: Dict[str, Any],
        persona: PersonaModel,
        context: Optional[Dict] = None
    ) -> Tuple[float, RiskLevel, Dict[str, Any]]:
        """
        Comprehensive risk assessment for a proposed action
        
        Returns:
            Tuple of (risk_score, risk_level, risk_details)
        """
        
        risk_scores = {}
        
        # Calculate individual risk factors
        risk_scores["financial_impact"] = self._assess_financial_risk(action)
        risk_scores["data_sensitivity"] = self._assess_data_sensitivity(action)
        risk_scores["reversibility"] = self._assess_reversibility(action)
        risk_scores["scope_of_impact"] = self._assess_scope(action)
        risk_scores["regulatory_compliance"] = self._assess_compliance(action)
        risk_scores["pattern_deviation"] = self._assess_pattern_deviation(action, persona)
        risk_scores["time_criticality"] = self._assess_time_criticality(action)
        
        # Calculate weighted risk score
        total_risk = sum(
            score * self.risk_factors[factor]
            for factor, score in risk_scores.items()
        )
        
        # Determine risk level
        risk_level = self._classify_risk_level(total_risk)
        
        # Generate risk details
        risk_details = {
            "score": total_risk,
            "level": risk_level.value,
            "factors": risk_scores,
            "explanation": self._generate_risk_explanation(risk_scores, risk_level),
            "mitigations": self._suggest_mitigations(risk_scores, action),
            "confidence": self._calculate_assessment_confidence(risk_scores)
        }
        
        return total_risk, risk_level, risk_details
    
    def _assess_financial_risk(self, action: Dict) -> float:
        """Assess financial impact risk"""
        
        amount = action.get("financial_amount", 0)
        
        if amount == 0:
            return 0.0
        elif amount < 1000:
            return 0.2
        elif amount < 10000:
            return 0.5
        elif amount < 100000:
            return 0.8
        else:
            return 1.0
    
    def _assess_data_sensitivity(self, action: Dict) -> float:
        """Assess data sensitivity risk"""
        
        data_types = action.get("data_types", [])
        
        sensitivity_scores = {
            "public": 0.1,
            "internal": 0.3,
            "confidential": 0.6,
            "personal_data": 0.8,
            "financial_data": 0.9,
            "health_data": 1.0,
            "security_credentials": 1.0
        }
        
        if not data_types:
            return 0.2
        
        # Return highest sensitivity score
        return max(sensitivity_scores.get(dt, 0.5) for dt in data_types)
    
    def _assess_reversibility(self, action: Dict) -> float:
        """Assess how easily an action can be reversed"""
        
        action_type = action.get("action_type", "").lower()
        
        # Irreversible actions
        if any(term in action_type for term in ["delete", "remove", "destroy", "purge"]):
            return 0.9
        
        # Difficult to reverse
        elif any(term in action_type for term in ["publish", "send", "deploy", "release"]):
            return 0.7
        
        # Moderately reversible
        elif any(term in action_type for term in ["update", "modify", "change"]):
            return 0.5
        
        # Easily reversible
        elif any(term in action_type for term in ["create", "add", "draft"]):
            return 0.3
        
        # Read-only actions
        elif any(term in action_type for term in ["read", "view", "list", "get"]):
            return 0.1
        
        else:
            return 0.4
    
    def _assess_scope(self, action: Dict) -> float:
        """Assess the scope of impact"""
        
        affected_users = action.get("affected_users", 1)
        affected_systems = action.get("affected_systems", [])
        
        # User impact scoring
        if affected_users == 1:
            user_score = 0.2
        elif affected_users < 10:
            user_score = 0.4
        elif affected_users < 100:
            user_score = 0.6
        elif affected_users < 1000:
            user_score = 0.8
        else:
            user_score = 1.0
        
        # System impact scoring
        system_score = min(len(affected_systems) * 0.2, 1.0)
        
        # Combined score (weighted average)
        return (user_score * 0.7) + (system_score * 0.3)
    
    def _assess_compliance(self, action: Dict) -> float:
        """Assess regulatory compliance risk"""
        
        compliance_areas = action.get("compliance_areas", [])
        
        if not compliance_areas:
            return 0.1
        
        high_risk_regulations = ["HIPAA", "GDPR", "SOX", "PCI-DSS", "FERPA", "CCPA"]
        medium_risk_regulations = ["ISO27001", "SOC2", "NIST", "CIS"]
        
        # Check for high-risk regulations
        if any(reg in high_risk_regulations for reg in compliance_areas):
            return 0.9
        
        # Check for medium-risk regulations
        elif any(reg in medium_risk_regulations for reg in compliance_areas):
            return 0.5
        
        else:
            return 0.3
    
    def _assess_pattern_deviation(self, action: Dict, persona: PersonaModel) -> float:
        """Assess deviation from normal behavioral patterns"""
        
        # Get persona's behavioral patterns
        common_actions = persona.communication_patterns.get("common_actions", []) if persona.communication_patterns else []
        
        action_type = action.get("action_type", "")
        
        # Check if action is in normal patterns
        if action_type in common_actions:
            base_deviation = 0.1
        else:
            base_deviation = 0.5
        
        # Adjust based on Fourth Ontology scores
        # High fear score + unusual action = higher risk
        if persona.fear_score > 0.7 and base_deviation > 0.3:
            base_deviation += 0.3
        
        # Low power score + autonomous action = higher risk
        if persona.power_score < 0.3 and action.get("requires_autonomy", False):
            base_deviation += 0.2
        
        return min(base_deviation, 0.95)
    
    def _assess_time_criticality(self, action: Dict) -> float:
        """Assess time criticality risk"""
        
        deadline = action.get("deadline")
        if not deadline:
            return 0.2
        
        # Convert to datetime if string
        if isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline)
        
        # Calculate hours until deadline
        time_until = (deadline - datetime.utcnow()).total_seconds() / 3600
        
        if time_until < 1:  # Less than 1 hour
            return 0.9
        elif time_until < 6:  # Less than 6 hours
            return 0.7
        elif time_until < 24:  # Less than 1 day
            return 0.5
        elif time_until < 72:  # Less than 3 days
            return 0.3
        else:
            return 0.1
    
    def _classify_risk_level(self, risk_score: float) -> RiskLevel:
        """Classify risk score into risk level"""
        
        if risk_score >= self.thresholds["critical"]:
            return RiskLevel.CRITICAL
        elif risk_score >= self.thresholds["high"]:
            return RiskLevel.HIGH
        elif risk_score >= self.thresholds["medium"]:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_risk_explanation(self, risk_scores: Dict, risk_level: RiskLevel) -> str:
        """Generate human-readable risk explanation"""
        
        # Sort risks by score
        sorted_risks = sorted(risk_scores.items(), key=lambda x: x[1], reverse=True)
        top_risks = sorted_risks[:3]
        
        explanation_parts = [f"Overall Risk: {risk_level.value.upper()}"]
        explanation_parts.append("Primary risk factors:")
        
        for factor, score in top_risks:
            if score > 0.3:
                factor_name = factor.replace("_", " ").title()
                severity = "High" if score > 0.7 else "Medium" if score > 0.4 else "Low"
                explanation_parts.append(f"• {factor_name}: {severity} ({score:.0%})")
        
        return "\n".join(explanation_parts)
    
    def _suggest_mitigations(self, risk_scores: Dict, action: Dict) -> List[str]:
        """Suggest risk mitigation strategies"""
        
        mitigations = []
        
        if risk_scores.get("financial_impact", 0) > 0.7:
            mitigations.append("Split into smaller transactions")
            mitigations.append("Add additional approval layer")
            mitigations.append("Implement spending limit controls")
        
        if risk_scores.get("data_sensitivity", 0) > 0.7:
            mitigations.append("Encrypt sensitive data")
            mitigations.append("Add audit logging")
            mitigations.append("Verify recipient authorization")
            mitigations.append("Use data masking where possible")
        
        if risk_scores.get("reversibility", 0) > 0.7:
            mitigations.append("Create backup before proceeding")
            mitigations.append("Implement soft-delete with recovery")
            mitigations.append("Add confirmation dialog")
        
        if risk_scores.get("scope_of_impact", 0) > 0.7:
            mitigations.append("Implement phased rollout")
            mitigations.append("Create rollback plan")
            mitigations.append("Test on subset first")
        
        if risk_scores.get("regulatory_compliance", 0) > 0.7:
            mitigations.append("Consult compliance team")
            mitigations.append("Document regulatory requirements")
            mitigations.append("Implement compliance checks")
        
        if risk_scores.get("pattern_deviation", 0) > 0.7:
            mitigations.append("Request explicit confirmation")
            mitigations.append("Document reason for deviation")
            mitigations.append("Add supervisor notification")
        
        if risk_scores.get("time_criticality", 0) > 0.7:
            mitigations.append("Escalate for priority review")
            mitigations.append("Set up automated reminders")
            mitigations.append("Implement deadline alerts")
        
        return mitigations[:5]  # Return top 5 most relevant
    
    def _calculate_assessment_confidence(self, risk_scores: Dict) -> float:
        """Calculate confidence in risk assessment"""
        
        # Higher confidence when risk factors are more extreme (close to 0 or 1)
        extremity_scores = [abs(score - 0.5) * 2 for score in risk_scores.values()]
        avg_extremity = np.mean(extremity_scores)
        
        # Base confidence on how extreme/clear the risk signals are
        base_confidence = 0.5 + (avg_extremity * 0.4)
        
        # Adjust based on number of high-risk factors
        high_risk_count = sum(1 for score in risk_scores.values() if score > 0.7)
        if high_risk_count >= 3:
            base_confidence += 0.1
        
        return min(base_confidence, 0.95)
    
    async def calculate_confidence_score(
        self,
        action: Dict,
        persona: PersonaModel,
        supporting_evidence: List[Dict]
    ) -> float:
        """
        Calculate confidence score for an action based on evidence
        
        Returns:
            Confidence score between 0 and 1
        """
        
        confidence_factors = {
            "historical_precedent": 0.3,
            "evidence_quality": 0.25,
            "pattern_match": 0.20,
            "ontology_alignment": 0.15,
            "recent_similar": 0.10
        }
        
        scores = {}
        
        # Historical precedent
        scores["historical_precedent"] = self._check_historical_precedent(action, persona)
        
        # Evidence quality
        scores["evidence_quality"] = self._assess_evidence_quality(supporting_evidence)
        
        # Pattern match
        scores["pattern_match"] = self._check_pattern_match(action, persona)
        
        # Ontology alignment
        scores["ontology_alignment"] = self._check_ontology_alignment(action, persona)
        
        # Recent similar actions
        scores["recent_similar"] = self._check_recent_similar(action, persona)
        
        # Calculate weighted confidence
        confidence = sum(
            score * confidence_factors[factor]
            for factor, score in scores.items()
        )
        
        return min(confidence, 1.0)
    
    def _check_historical_precedent(self, action: Dict, persona: PersonaModel) -> float:
        """Check if similar action has been done before"""
        
        # Check if action type exists in historical patterns
        if persona.communication_patterns:
            common_actions = persona.communication_patterns.get("common_actions", [])
            if action.get("action_type") in common_actions:
                return 0.9
        
        # Check for partial matches
        action_keywords = set(action.get("action_type", "").lower().split())
        historical_match_score = 0.0
        
        if persona.decision_patterns:
            historical_keywords = set()
            for pattern in persona.decision_patterns.get("patterns", []):
                historical_keywords.update(str(pattern).lower().split())
            
            overlap = len(action_keywords & historical_keywords)
            if overlap > 0:
                historical_match_score = min(overlap * 0.2, 0.7)
        
        return historical_match_score
    
    def _assess_evidence_quality(self, evidence: List[Dict]) -> float:
        """Assess quality of supporting evidence"""
        
        if not evidence:
            return 0.1
        
        # Score based on evidence quantity (diminishing returns)
        quantity_score = min(len(evidence) * 0.1, 0.5)
        
        # Score based on evidence recency
        recency_scores = []
        for item in evidence:
            if "timestamp" in item:
                # Calculate age in days
                age_days = (datetime.utcnow() - datetime.fromisoformat(item["timestamp"])).days
                if age_days < 7:
                    recency_scores.append(1.0)
                elif age_days < 30:
                    recency_scores.append(0.7)
                elif age_days < 90:
                    recency_scores.append(0.4)
                else:
                    recency_scores.append(0.2)
        
        recency_score = np.mean(recency_scores) if recency_scores else 0.3
        
        # Combine scores
        return (quantity_score + recency_score) / 2
    
    def _check_pattern_match(self, action: Dict, persona: PersonaModel) -> float:
        """Check if action matches behavioral patterns"""
        
        pattern_score = 0.5  # Neutral baseline
        
        # Check communication patterns
        if persona.communication_patterns:
            style = persona.communication_patterns.get("style", {})
            
            # Match formality
            if action.get("formality_level") == style.get("formality"):
                pattern_score += 0.15
            
            # Match urgency handling
            if action.get("urgency") == style.get("typical_urgency"):
                pattern_score += 0.15
        
        # Check decision patterns
        if persona.decision_patterns:
            patterns = persona.decision_patterns.get("patterns", {})
            
            # Match decision speed
            if action.get("requires_quick_decision") == patterns.get("prefers_quick_decisions"):
                pattern_score += 0.1
            
            # Match collaboration preference
            if action.get("requires_collaboration") == patterns.get("prefers_collaboration"):
                pattern_score += 0.1
        
        return min(pattern_score, 0.95)
    
    def _check_ontology_alignment(self, action: Dict, persona: PersonaModel) -> float:
        """Check alignment with Fourth Ontology dimensions"""
        
        alignment_score = 0.0
        checks = 0
        
        # Decision dimension
        if action.get("requires_analysis"):
            expected_analysis = persona.decision_score > 0.6
            if action.get("requires_analysis") == expected_analysis:
                alignment_score += 1.0
            checks += 1
        
        # Power dimension
        if "autonomous_execution" in action:
            expected_autonomy = persona.power_score > 0.6
            if action["autonomous_execution"] == expected_autonomy:
                alignment_score += 1.0
            checks += 1
        
        # Fear dimension
        if "risk_level" in action:
            risk_tolerance = 1 - persona.fear_score
            action_risk = {"low": 0.2, "medium": 0.5, "high": 0.8}.get(action["risk_level"], 0.5)
            alignment = 1 - abs(risk_tolerance - action_risk)
            alignment_score += alignment
            checks += 1
        
        # Reward dimension
        if "external_visibility" in action:
            expects_recognition = persona.reward_score > 0.6
            if action["external_visibility"] == expects_recognition:
                alignment_score += 1.0
            checks += 1
        
        # Meaning dimension
        if "strategic_importance" in action:
            values_strategic = persona.meaning_score > 0.6
            if action["strategic_importance"] == values_strategic:
                alignment_score += 1.0
            checks += 1
        
        return alignment_score / checks if checks > 0 else 0.5
    
    def _check_recent_similar(self, action: Dict, persona: PersonaModel) -> float:
        """Check for recent similar actions"""
        
        # This would check recent action history
        # For now, return a moderate score
        return 0.6
    
    def get_risk_summary(self, persona_id: int, days: int = 30) -> Dict[str, Any]:
        """Get risk assessment summary for a persona"""
        
        # This would aggregate risk data from the database
        return {
            "persona_id": persona_id,
            "period_days": days,
            "risk_distribution": {
                "low": 45,
                "medium": 30,
                "high": 20,
                "critical": 5
            },
            "average_risk_score": 0.42,
            "highest_risk_factors": [
                "data_sensitivity",
                "financial_impact",
                "pattern_deviation"
            ]
        }
