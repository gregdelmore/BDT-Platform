"""
Negative Space Analysis Service
Identifies and enforces behavioral boundaries - what the persona DOESN'T do
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import numpy as np
import json
import re

from core.config import settings
from core.models import (
    PersonaModel, 
    NegativeSpace, 
    RiskLevel,
    BehavioralPattern,
    HILTAction,
    ApprovalStatus
)

class NegativeSpaceAnalyzer:
    """
    Analyzes historical data to identify behavioral boundaries.
    Critical for safety in L4 autonomous operation.
    """
    
    def __init__(self, db: Session):
        self.db = db
        
        # Analysis configuration
        self.confidence_threshold = settings.NEGATIVE_SPACE_CONFIDENCE_THRESHOLD
        self.min_evidence_count = settings.NEGATIVE_SPACE_MIN_EVIDENCE
        
        # Pattern categories
        self.categories = {
            "tasks": {
                "description": "Tasks never performed",
                "risk_weight": 0.8,
                "examples": ["production_deployment", "financial_approval", "customer_contact"]
            },
            "tools": {
                "description": "Tools/systems never used", 
                "risk_weight": 0.9,
                "examples": ["production_db", "payment_gateway", "security_console"]
            },
            "times": {
                "description": "Time-based boundaries",
                "risk_weight": 0.3,
                "examples": ["weekend_work", "late_night_access", "holiday_activity"]
            },
            "decisions": {
                "description": "Decisions never made autonomously",
                "risk_weight": 1.0,
                "examples": ["budget_approval", "hiring_decision", "contract_signing"]
            },
            "communications": {
                "description": "Communication boundaries",
                "risk_weight": 0.5,
                "examples": ["executive_contact", "customer_communication", "public_statements"]
            }
        }
        
        # Risk classification rules
        self.risk_rules = {
            "financial": RiskLevel.CRITICAL,
            "production": RiskLevel.HIGH,
            "customer": RiskLevel.HIGH,
            "security": RiskLevel.CRITICAL,
            "legal": RiskLevel.CRITICAL,
            "internal": RiskLevel.MEDIUM,
            "documentation": RiskLevel.LOW,
            "testing": RiskLevel.LOW
        }
    
    async def analyze_negative_spaces(
        self,
        persona_id: int,
        historical_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze historical data to identify negative space patterns
        
        Args:
            persona_id: ID of the persona to analyze
            historical_data: Dictionary containing historical activity data
            
        Returns:
            List of identified negative space boundaries
        """
        
        persona = self.db.query(PersonaModel).filter_by(id=persona_id).first()
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")
        
        negative_spaces = []
        
        # Analyze each category
        for category in self.categories.keys():
            category_boundaries = await self._analyze_category(
                category,
                historical_data,
                persona
            )
            negative_spaces.extend(category_boundaries)
        
        # Store or update in database
        for space_def in negative_spaces:
            self._store_negative_space(persona_id, space_def)
        
        # Commit changes
        self.db.commit()
        
        # Return summary
        return self._create_boundary_summary(negative_spaces)
    
    async def _analyze_category(
        self,
        category: str,
        data: Dict[str, Any],
        persona: PersonaModel
    ) -> List[Dict[str, Any]]:
        """
        Analyze a specific category for negative space patterns
        """
        
        boundaries = []
        
        if category == "tasks":
            boundaries = await self._analyze_task_boundaries(data, persona)
        elif category == "tools":
            boundaries = await self._analyze_tool_boundaries(data, persona)
        elif category == "times":
            boundaries = await self._analyze_temporal_boundaries(data, persona)
        elif category == "decisions":
            boundaries = await self._analyze_decision_boundaries(data, persona)
        elif category == "communications":
            boundaries = await self._analyze_communication_boundaries(data, persona)
        
        return boundaries
    
    async def _analyze_task_boundaries(
        self,
        data: Dict[str, Any],
        persona: PersonaModel
    ) -> List[Dict[str, Any]]:
        """
        Identify tasks that are never performed
        """
        
        boundaries = []
        
        # Extract all possible tasks from organizational context
        all_tasks = self._extract_organizational_tasks(data)
        
        # Extract tasks performed by this persona
        performed_tasks = self._extract_performed_tasks(data, persona)
        
        # Identify never-performed tasks
        never_performed = all_tasks - performed_tasks
        
        for task in never_performed:
            # Assess risk level
            risk_level = self._classify_task_risk(task)
            
            # Calculate confidence based on evidence
            confidence = self._calculate_pattern_confidence(
                len(performed_tasks),
                len(all_tasks),
                task
            )
            
            if confidence >= self.confidence_threshold:
                boundaries.append({
                    "category": "tasks",
                    "pattern": f"Never performs: {task}",
                    "description": f"No evidence of performing {task} in historical data",
                    "risk_level": risk_level,
                    "evidence_count": len(performed_tasks),
                    "confidence": confidence,
                    "override_allowed": risk_level not in [RiskLevel.HIGH, RiskLevel.CRITICAL],
                    "metadata": {
                        "task_type": self._categorize_task(task),
                        "similar_performed": self._find_similar_tasks(task, performed_tasks)
                    }
                })
        
        return boundaries
    
    async def _analyze_tool_boundaries(
        self,
        data: Dict[str, Any],
        persona: PersonaModel
    ) -> List[Dict[str, Any]]:
        """
        Identify tools and systems never used
        """
        
        boundaries = []
        
        # Extract available tools
        available_tools = self._extract_available_tools(data)
        
        # Extract used tools
        used_tools = self._extract_used_tools(data, persona)
        
        # Identify never-used tools
        never_used = available_tools - used_tools
        
        for tool in never_used:
            # Check if it's a critical system
            is_critical = self._is_critical_system(tool)
            
            risk_level = RiskLevel.CRITICAL if is_critical else RiskLevel.MEDIUM
            
            boundaries.append({
                "category": "tools",
                "pattern": f"Never uses: {tool}",
                "description": f"No evidence of using {tool} system/tool",
                "risk_level": risk_level,
                "evidence_count": len(used_tools),
                "confidence": 0.95 if is_critical else 0.85,
                "override_allowed": not is_critical,
                "metadata": {
                    "tool_type": self._categorize_tool(tool),
                    "criticality": "critical" if is_critical else "standard",
                    "alternatives_used": self._find_alternative_tools(tool, used_tools)
                }
            })
        
        return boundaries
    
    async def _analyze_temporal_boundaries(
        self,
        data: Dict[str, Any],
        persona: PersonaModel
    ) -> List[Dict[str, Any]]:
        """
        Identify time-based boundaries
        """
        
        boundaries = []
        
        # Extract activity timestamps
        activity_times = self._extract_activity_times(data, persona)
        
        # Analyze work hour patterns
        work_hours = self._analyze_work_hours(activity_times)
        
        # Find never-work times
        if work_hours["never_hours"]:
            boundaries.append({
                "category": "times",
                "pattern": f"Never works: {work_hours['never_hours']}",
                "description": "No activity detected during these hours",
                "risk_level": RiskLevel.LOW,
                "evidence_count": len(activity_times),
                "confidence": 0.9,
                "override_allowed": True,
                "metadata": {
                    "typical_hours": work_hours["typical_hours"],
                    "weekend_activity": work_hours["weekend_activity"],
                    "timezone": work_hours.get("timezone", "UTC")
                }
            })
        
        # Analyze deadline patterns
        deadline_patterns = self._analyze_deadline_patterns(data, persona)
        
        if deadline_patterns["always_early"]:
            boundaries.append({
                "category": "times",
                "pattern": "Never misses deadlines",
                "description": f"Consistently delivers {deadline_patterns['avg_early_hours']} hours early",
                "risk_level": RiskLevel.MEDIUM,
                "evidence_count": deadline_patterns["sample_size"],
                "confidence": 0.85,
                "override_allowed": True,
                "metadata": deadline_patterns
            })
        
        return boundaries
    
    async def _analyze_decision_boundaries(
        self,
        data: Dict[str, Any],
        persona: PersonaModel
    ) -> List[Dict[str, Any]]:
        """
        Identify decision-making boundaries
        """
        
        boundaries = []
        
        # Extract decision patterns
        decisions = self._extract_decisions(data, persona)
        
        # Find decisions always escalated
        escalated_types = self._find_escalated_decisions(decisions)
        
        for decision_type in escalated_types:
            risk_level = self._classify_decision_risk(decision_type)
            
            boundaries.append({
                "category": "decisions",
                "pattern": f"Never decides alone: {decision_type}",
                "description": f"Always seeks approval for {decision_type} decisions",
                "risk_level": risk_level,
                "evidence_count": len(decisions),
                "confidence": 0.88,
                "override_allowed": False,  # Decision boundaries are strict
                "metadata": {
                    "decision_category": self._categorize_decision(decision_type),
                    "typical_approvers": self._find_typical_approvers(decision_type, decisions),
                    "escalation_time": self._calculate_avg_escalation_time(decision_type, decisions)
                }
            })
        
        # Analyze approval limits
        approval_limits = self._extract_approval_limits(decisions)
        
        if approval_limits["has_limit"]:
            boundaries.append({
                "category": "decisions",
                "pattern": f"Never approves above: ${approval_limits['max_amount']}",
                "description": "Financial approval limit detected",
                "risk_level": RiskLevel.HIGH,
                "evidence_count": approval_limits["sample_size"],
                "confidence": 0.92,
                "override_allowed": False,
                "metadata": approval_limits
            })
        
        return boundaries
    
    async def _analyze_communication_boundaries(
        self,
        data: Dict[str, Any],
        persona: PersonaModel
    ) -> List[Dict[str, Any]]:
        """
        Identify communication boundaries
        """
        
        boundaries = []
        
        # Extract communication patterns
        communications = self._extract_communications(data, persona)
        
        # Analyze recipient patterns
        all_recipients = self._extract_all_recipients(data)
        contacted_recipients = self._extract_contacted_recipients(communications)
        
        never_contacted = all_recipients - contacted_recipients
        
        # Identify high-level contacts never made
        for recipient in never_contacted:
            if self._is_high_level_contact(recipient):
                boundaries.append({
                    "category": "communications",
                    "pattern": f"Never contacts: {recipient['level']} level",
                    "description": f"No direct communication with {recipient['level']} executives",
                    "risk_level": RiskLevel.MEDIUM,
                    "evidence_count": len(contacted_recipients),
                    "confidence": 0.85,
                    "override_allowed": True,
                    "metadata": {
                        "organizational_level": recipient['level'],
                        "typical_communication_path": self._find_communication_path(recipient)
                    }
                })
        
        return boundaries
    
    def check_boundary_violation(
        self,
        persona_id: int,
        proposed_action: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a proposed action violates any negative space boundaries
        
        Args:
            persona_id: ID of the persona
            proposed_action: Dictionary describing the proposed action
            
        Returns:
            Violation details if boundary is violated, None otherwise
        """
        
        # Get active boundaries for persona
        boundaries = (
            self.db.query(NegativeSpace)
            .filter_by(persona_id=persona_id, is_active=True)
            .all()
        )
        
        violations = []
        
        for boundary in boundaries:
            if self._action_violates_boundary(proposed_action, boundary):
                violations.append({
                    "boundary_id": boundary.id,
                    "pattern": boundary.pattern,
                    "category": boundary.category,
                    "risk_level": boundary.risk_level.value,
                    "confidence": boundary.confidence,
                    "override_allowed": boundary.override_allowed
                })
        
        if violations:
            # Return the highest risk violation
            highest_risk = max(violations, key=lambda v: self._risk_priority(v["risk_level"]))
            return {
                "violated": True,
                "violations": violations,
                "primary_violation": highest_risk,
                "total_violations": len(violations)
            }
        
        return None
    
    def _action_violates_boundary(
        self,
        action: Dict[str, Any],
        boundary: NegativeSpace
    ) -> bool:
        """
        Check if an action violates a specific boundary
        """
        
        # Extract boundary pattern
        pattern_text = boundary.pattern.lower()
        
        if boundary.category == "tasks":
            if "never performs:" in pattern_text:
                task = pattern_text.replace("never performs:", "").strip()
                action_type = action.get("action_type", "").lower()
                return self._fuzzy_match(task, action_type)
        
        elif boundary.category == "tools":
            if "never uses:" in pattern_text:
                tool = pattern_text.replace("never uses:", "").strip()
                tools = action.get("tools_required", [])
                return any(self._fuzzy_match(tool, t) for t in tools)
        
        elif boundary.category == "times":
            current_time = datetime.now()
            
            if "never works:" in pattern_text:
                restricted_hours = self._parse_time_restriction(pattern_text)
                return self._time_in_restriction(current_time, restricted_hours)
        
        elif boundary.category == "decisions":
            if "never decides alone:" in pattern_text:
                decision_type = pattern_text.replace("never decides alone:", "").strip()
                return self._fuzzy_match(decision_type, action.get("decision_type", ""))
            
            if "never approves above:" in pattern_text:
                limit = self._parse_amount(pattern_text)
                return action.get("amount", 0) > limit
        
        elif boundary.category == "communications":
            if "never contacts:" in pattern_text:
                level = pattern_text.replace("never contacts:", "").strip()
                recipients = action.get("recipients", [])
                return any(self._is_restricted_contact(r, level) for r in recipients)
        
        return False
    
    def toggle_boundary(
        self,
        boundary_id: int,
        user_email: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Toggle a negative space boundary on/off
        """
        
        boundary = self.db.query(NegativeSpace).filter_by(id=boundary_id).first()
        if not boundary:
            raise ValueError(f"Boundary {boundary_id} not found")
        
        if not boundary.override_allowed:
            raise ValueError(f"Boundary {boundary_id} cannot be overridden (high risk)")
        
        # Toggle state
        boundary.is_active = not boundary.is_active
        boundary.updated_at = datetime.utcnow()
        
        # Log the change
        from core.models import AuditLog
        
        audit_log = AuditLog(
            persona_id=boundary.persona_id,
            event_type="boundary_toggle",
            event_category="negative_space",
            event_data={
                "boundary_id": boundary_id,
                "pattern": boundary.pattern,
                "new_state": "active" if boundary.is_active else "inactive",
                "reason": reason
            },
            user_email=user_email
        )
        self.db.add(audit_log)
        
        self.db.commit()
        
        return {
            "boundary_id": boundary_id,
            "pattern": boundary.pattern,
            "is_active": boundary.is_active,
            "toggled_by": user_email,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_boundaries(
        self,
        persona_id: int,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get negative space boundaries for a persona
        """
        
        query = self.db.query(NegativeSpace).filter_by(persona_id=persona_id)
        
        if category:
            query = query.filter_by(category=category)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        boundaries = query.all()
        
        return [
            {
                "id": b.id,
                "category": b.category,
                "pattern": b.pattern,
                "description": b.description,
                "risk_level": b.risk_level.value,
                "confidence": b.confidence,
                "evidence_count": b.evidence_count,
                "is_active": b.is_active,
                "override_allowed": b.override_allowed,
                "violation_count": b.violation_count,
                "last_violated": b.last_violated.isoformat() if b.last_violated else None,
                "created_at": b.created_at.isoformat()
            }
            for b in boundaries
        ]
    
    def record_violation(
        self,
        boundary_id: int,
        action_details: Dict[str, Any]
    ):
        """
        Record a boundary violation
        """
        
        boundary = self.db.query(NegativeSpace).filter_by(id=boundary_id).first()
        if boundary:
            boundary.violation_count += 1
            boundary.last_violated = datetime.utcnow()
            self.db.commit()
    
    # Helper methods
    def _store_negative_space(
        self,
        persona_id: int,
        space_def: Dict[str, Any]
    ):
        """
        Store or update a negative space boundary
        """
        
        # Check for existing boundary
        existing = self.db.query(NegativeSpace).filter_by(
            persona_id=persona_id,
            category=space_def["category"],
            pattern=space_def["pattern"]
        ).first()
        
        if existing:
            # Update confidence and evidence
            existing.confidence = max(existing.confidence, space_def["confidence"])
            existing.evidence_count = space_def["evidence_count"]
            existing.updated_at = datetime.utcnow()
        else:
            # Create new boundary
            boundary = NegativeSpace(
                persona_id=persona_id,
                category=space_def["category"],
                pattern=space_def["pattern"],
                description=space_def.get("description", ""),
                risk_level=space_def["risk_level"],
                evidence_count=space_def["evidence_count"],
                confidence=space_def["confidence"],
                override_allowed=space_def["override_allowed"]
            )
            self.db.add(boundary)
    
    def _extract_organizational_tasks(self, data: Dict) -> Set[str]:
        """Extract all possible tasks from organizational data"""
        # Implementation would analyze organizational data
        return set(data.get("all_tasks", []))
    
    def _extract_performed_tasks(self, data: Dict, persona: PersonaModel) -> Set[str]:
        """Extract tasks performed by the persona"""
        # Implementation would analyze persona's historical data
        return set(data.get("performed_tasks", []))
    
    def _classify_task_risk(self, task: str) -> RiskLevel:
        """Classify the risk level of a task"""
        task_lower = task.lower()
        
        for keyword, risk_level in self.risk_rules.items():
            if keyword in task_lower:
                return risk_level
        
        return RiskLevel.LOW
    
    def _calculate_pattern_confidence(
        self,
        evidence_count: int,
        total_possible: int,
        pattern: str
    ) -> float:
        """Calculate confidence score for a pattern"""
        
        if evidence_count < self.min_evidence_count:
            return 0.0
        
        # Base confidence from evidence ratio
        base_confidence = min(0.5 + (evidence_count / total_possible), 0.95)
        
        # Adjust for critical patterns
        if any(critical in pattern.lower() for critical in ["production", "financial", "security"]):
            base_confidence = min(base_confidence + 0.1, 0.99)
        
        return base_confidence
    
    def _is_critical_system(self, tool: str) -> bool:
        """Check if a tool is a critical system"""
        critical_keywords = [
            "production", "payment", "customer_data",
            "financial", "security", "compliance"
        ]
        return any(keyword in tool.lower() for keyword in critical_keywords)
    
    def _fuzzy_match(self, pattern: str, text: str) -> bool:
        """Fuzzy string matching"""
        # Simple implementation - could use more sophisticated matching
        pattern_words = set(pattern.lower().split())
        text_words = set(text.lower().split())
        
        # Check for significant overlap
        overlap = pattern_words & text_words
        return len(overlap) >= len(pattern_words) * 0.5
    
    def _risk_priority(self, risk_level: str) -> int:
        """Get numeric priority for risk level"""
        priorities = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
        return priorities.get(risk_level, 0)
    
    def _create_boundary_summary(self, boundaries: List[Dict]) -> List[Dict]:
        """Create summary of boundaries"""
        
        summary = []
        
        # Group by category
        by_category = {}
        for boundary in boundaries:
            cat = boundary["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(boundary)
        
        # Create summary for each category
        for category, items in by_category.items():
            summary.append({
                "category": category,
                "description": self.categories[category]["description"],
                "boundary_count": len(items),
                "risk_distribution": self._calculate_risk_distribution(items),
                "average_confidence": np.mean([b["confidence"] for b in items]),
                "boundaries": items[:5]  # Top 5 for preview
            })
        
        return summary
    
    def _calculate_risk_distribution(self, boundaries: List[Dict]) -> Dict[str, int]:
        """Calculate distribution of risk levels"""
        
        distribution = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for boundary in boundaries:
            risk = boundary["risk_level"].value if hasattr(boundary["risk_level"], "value") else boundary["risk_level"]
            distribution[risk] = distribution.get(risk, 0) + 1
        
        return distribution
    
    # Placeholder methods for specific analyses
    def _extract_available_tools(self, data: Dict) -> Set[str]:
        """Extract available tools from organizational data"""
        return set(data.get("available_tools", []))
    
    def _extract_used_tools(self, data: Dict, persona: PersonaModel) -> Set[str]:
        """Extract tools used by persona"""
        return set(data.get("used_tools", []))
    
    def _extract_activity_times(self, data: Dict, persona: PersonaModel) -> List[datetime]:
        """Extract activity timestamps"""
        return data.get("activity_times", [])
    
    def _analyze_work_hours(self, times: List[datetime]) -> Dict:
        """Analyze work hour patterns"""
        return {
            "typical_hours": "9AM-5PM",
            "never_hours": "12AM-6AM",
            "weekend_activity": False
        }
    
    def _analyze_deadline_patterns(self, data: Dict, persona: PersonaModel) -> Dict:
        """Analyze deadline adherence patterns"""
        return {
            "always_early": True,
            "avg_early_hours": 24,
            "sample_size": 50
        }
    
    def _extract_decisions(self, data: Dict, persona: PersonaModel) -> List[Dict]:
        """Extract decision data"""
        return data.get("decisions", [])
    
    def _find_escalated_decisions(self, decisions: List[Dict]) -> Set[str]:
        """Find decision types that are always escalated"""
        return set(data.get("escalated_types", []))
    
    def _classify_decision_risk(self, decision_type: str) -> RiskLevel:
        """Classify risk level of a decision type"""
        if "financial" in decision_type.lower():
            return RiskLevel.HIGH
        return RiskLevel.MEDIUM
    
    def _extract_approval_limits(self, decisions: List[Dict]) -> Dict:
        """Extract financial approval limits"""
        return {
            "has_limit": True,
            "max_amount": 10000,
            "sample_size": 25
        }
    
    def _categorize_task(self, task: str) -> str:
        """Categorize a task"""
        return "operational"
    
    def _find_similar_tasks(self, task: str, performed: Set[str]) -> List[str]:
        """Find similar tasks that are performed"""
        return []
    
    def _categorize_tool(self, tool: str) -> str:
        """Categorize a tool"""
        return "system"
    
    def _find_alternative_tools(self, tool: str, used: Set[str]) -> List[str]:
        """Find alternative tools that are used"""
        return []
    
    def _categorize_decision(self, decision: str) -> str:
        """Categorize a decision"""
        return "operational"
    
    def _find_typical_approvers(self, decision_type: str, decisions: List[Dict]) -> List[str]:
        """Find typical approvers for a decision type"""
        return ["manager", "director"]
    
    def _calculate_avg_escalation_time(self, decision_type: str, decisions: List[Dict]) -> float:
        """Calculate average escalation time"""
        return 24.0  # hours
    
    def _extract_communications(self, data: Dict, persona: PersonaModel) -> List[Dict]:
        """Extract communication data"""
        return data.get("communications", [])
    
    def _extract_all_recipients(self, data: Dict) -> Set[Dict]:
        """Extract all possible recipients"""
        return set()
    
    def _extract_contacted_recipients(self, communications: List[Dict]) -> Set[Dict]:
        """Extract actually contacted recipients"""
        return set()
    
    def _is_high_level_contact(self, recipient: Dict) -> bool:
        """Check if recipient is high-level"""
        return recipient.get("level") in ["executive", "c-suite"]
    
    def _find_communication_path(self, recipient: Dict) -> List[str]:
        """Find typical communication path to recipient"""
        return ["manager", "director", recipient.get("level")]
    
    def _parse_time_restriction(self, pattern: str) -> Dict:
        """Parse time restriction from pattern"""
        return {"start": 0, "end": 6}
    
    def _time_in_restriction(self, time: datetime, restriction: Dict) -> bool:
        """Check if time falls within restriction"""
        hour = time.hour
        return restriction["start"] <= hour < restriction["end"]
    
    def _parse_amount(self, pattern: str) -> float:
        """Parse amount from pattern"""
        import re
        match = re.search(r'\$?([\d,]+)', pattern)
        if match:
            return float(match.group(1).replace(',', ''))
        return 0.0
    
    def _is_restricted_contact(self, recipient: str, level: str) -> bool:
        """Check if recipient is at restricted level"""
        # Implementation would check recipient's organizational level
        return False
