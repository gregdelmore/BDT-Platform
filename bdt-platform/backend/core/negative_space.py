"""
Negative Space Analysis - Behavioral boundary detection and enforcement
"""
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import re
import logging
from dataclasses import dataclass
from enum import Enum

from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

from ..config import settings
from ..database import (
    get_db, NegativeSpaceBoundary, BoundaryViolation,
    BoundaryRiskLevel, Persona, DelegatedTask
)

logger = logging.getLogger(__name__)

class BoundaryCategory(str, Enum):
    """Categories of negative space boundaries"""
    TEMPORAL = "temporal"       # Time-based boundaries
    TECHNICAL = "technical"      # Technology/tool boundaries
    SOCIAL = "social"           # Interpersonal boundaries
    PROCESS = "process"         # Workflow boundaries
    FINANCIAL = "financial"     # Financial/billing boundaries
    AUTHORITY = "authority"     # Decision authority boundaries

@dataclass
class BoundaryCheck:
    """Result of checking a boundary"""
    boundary_id: str
    violated: bool
    severity: float  # 0-1 scale
    distance_to_boundary: float  # How close to violation
    recommendation: str
    evidence: List[str]

class NegativeSpaceAnalyzer:
    """
    Analyzer for detecting and enforcing behavioral boundaries
    """
    
    def __init__(self):
        self.risk_thresholds = settings.BOUNDARY_RISK_LEVELS
        self.enforcement_mode = settings.BOUNDARY_ENFORCEMENT_MODE
        
        # Pattern matchers for common boundaries
        self.temporal_patterns = {
            "weekend": r"(saturday|sunday|weekend)",
            "after_hours": r"(evening|night|after.?hours|late)",
            "morning": r"(early.?morning|before.?9|dawn)",
            "friday_pm": r"(friday.?(afternoon|evening|pm))"
        }
        
        self.technical_patterns = {
            "production": r"(production|prod|live.?system)",
            "database": r"(database|db|sql|query)",
            "deployment": r"(deploy|rollout|release)",
            "security": r"(security|auth|credential|password)"
        }
        
        self.social_patterns = {
            "executive": r"(ceo|cto|executive|c-level|board)",
            "customer": r"(customer|client|user)",
            "vendor": r"(vendor|supplier|partner)",
            "external": r"(external|outside|third.?party)"
        }
    
    def extract_boundaries(
        self,
        persona_id: str,
        activity_data: List[Dict],
        min_evidence: int = 3
    ) -> List[NegativeSpaceBoundary]:
        """
        Extract negative space boundaries from activity patterns
        """
        logger.info(f"Extracting boundaries for persona {persona_id}")
        
        boundaries = []
        
        # Temporal boundaries
        temporal_boundaries = self._extract_temporal_boundaries(
            persona_id, activity_data, min_evidence
        )
        boundaries.extend(temporal_boundaries)
        
        # Technical boundaries
        technical_boundaries = self._extract_technical_boundaries(
            persona_id, activity_data, min_evidence
        )
        boundaries.extend(technical_boundaries)
        
        # Social boundaries
        social_boundaries = self._extract_social_boundaries(
            persona_id, activity_data, min_evidence
        )
        boundaries.extend(social_boundaries)
        
        # Process boundaries
        process_boundaries = self._extract_process_boundaries(
            persona_id, activity_data, min_evidence
        )
        boundaries.extend(process_boundaries)
        
        # Store boundaries in database
        self._store_boundaries(boundaries)
        
        logger.info(f"Extracted {len(boundaries)} boundaries")
        return boundaries
    
    def check_boundaries(
        self,
        persona_id: str,
        task: DelegatedTask,
        context: Dict[str, Any]
    ) -> List[BoundaryCheck]:
        """
        Check if a task violates any boundaries
        """
        checks = []
        
        try:
            with get_db() as db:
                # Get active boundaries for persona
                boundaries = db.query(NegativeSpaceBoundary).filter(
                    NegativeSpaceBoundary.persona_id == persona_id,
                    NegativeSpaceBoundary.is_active == True
                ).all()
                
                for boundary in boundaries:
                    check = self._check_single_boundary(boundary, task, context)
                    checks.append(check)
                    
                    # Record violation if detected
                    if check.violated:
                        self._record_violation(boundary.id, task.id, check)
                
                return checks
                
        except Exception as e:
            logger.error(f"Boundary check failed: {str(e)}")
            return []
    
    def enforce_boundaries(
        self,
        checks: List[BoundaryCheck],
        task: DelegatedTask
    ) -> Tuple[bool, str]:
        """
        Enforce boundaries based on check results
        
        Returns: (allow_execution, reason)
        """
        if not checks:
            return True, "No boundaries to check"
        
        # Check for critical violations
        critical_violations = [c for c in checks if c.violated and c.severity > 0.8]
        if critical_violations:
            reason = f"Critical boundary violation: {critical_violations[0].recommendation}"
            return False, reason
        
        # Check enforcement mode
        if self.enforcement_mode == "strict":
            # Block any violation
            violations = [c for c in checks if c.violated]
            if violations:
                return False, f"Boundary violation: {violations[0].recommendation}"
        
        elif self.enforcement_mode == "flexible":
            # Block only high-severity violations
            high_violations = [c for c in checks if c.violated and c.severity > 0.6]
            if high_violations:
                return False, f"High-risk boundary violation: {high_violations[0].recommendation}"
        
        elif self.enforcement_mode == "learning":
            # Allow with logging for learning
            violations = [c for c in checks if c.violated]
            if violations:
                logger.warning(f"Learning mode: Allowing task despite {len(violations)} violations")
        
        return True, "Boundaries checked - execution allowed"
    
    def update_boundary_confidence(
        self,
        boundary_id: str,
        feedback: str,
        adjustment: float
    ) -> bool:
        """
        Update boundary confidence based on feedback
        """
        try:
            with get_db() as db:
                boundary = db.query(NegativeSpaceBoundary).filter(
                    NegativeSpaceBoundary.id == boundary_id
                ).first()
                
                if not boundary:
                    return False
                
                # Adjust confidence
                old_confidence = boundary.confidence
                boundary.confidence = max(0, min(1, boundary.confidence + adjustment))
                
                # Update metadata
                if not boundary.metadata:
                    boundary.metadata = {}
                
                if "confidence_history" not in boundary.metadata:
                    boundary.metadata["confidence_history"] = []
                
                boundary.metadata["confidence_history"].append({
                    "old_confidence": old_confidence,
                    "new_confidence": boundary.confidence,
                    "adjustment": adjustment,
                    "feedback": feedback,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to update boundary confidence: {str(e)}")
            return False
    
    def get_boundary_statistics(self, persona_id: str) -> Dict[str, Any]:
        """
        Get statistics about boundaries for a persona
        """
        try:
            with get_db() as db:
                boundaries = db.query(NegativeSpaceBoundary).filter(
                    NegativeSpaceBoundary.persona_id == persona_id
                ).all()
                
                violations = db.query(BoundaryViolation).join(
                    NegativeSpaceBoundary
                ).filter(
                    NegativeSpaceBoundary.persona_id == persona_id
                ).all()
                
                stats = {
                    "total_boundaries": len(boundaries),
                    "active_boundaries": sum(1 for b in boundaries if b.is_active),
                    "guardrails": sum(1 for b in boundaries if b.is_guardrail),
                    "total_violations": len(violations),
                    "recent_violations": sum(
                        1 for v in violations 
                        if v.occurred_at > datetime.utcnow() - timedelta(days=7)
                    ),
                    "boundaries_by_category": defaultdict(int),
                    "boundaries_by_risk": defaultdict(int),
                    "violation_rate": 0
                }
                
                for boundary in boundaries:
                    stats["boundaries_by_category"][boundary.category or "uncategorized"] += 1
                    stats["boundaries_by_risk"][boundary.risk_level.value] += 1
                
                # Calculate violation rate
                if boundaries:
                    violated_boundaries = set(v.boundary_id for v in violations)
                    stats["violation_rate"] = len(violated_boundaries) / len(boundaries)
                
                return dict(stats)
                
        except Exception as e:
            logger.error(f"Failed to get boundary statistics: {str(e)}")
            return {}
    
    def _extract_temporal_boundaries(
        self,
        persona_id: str,
        activity_data: List[Dict],
        min_evidence: int
    ) -> List[NegativeSpaceBoundary]:
        """Extract time-based boundaries"""
        boundaries = []
        
        # Analyze activity timestamps
        timestamps = [
            datetime.fromisoformat(d["timestamp"])
            for d in activity_data
            if "timestamp" in d
        ]
        
        if len(timestamps) < min_evidence:
            return boundaries
        
        # Weekend activity analysis
        weekend_activities = [
            t for t in timestamps
            if t.weekday() in [5, 6]  # Saturday, Sunday
        ]
        
        if len(weekend_activities) < len(timestamps) * 0.05:  # Less than 5% weekend activity
            boundaries.append(NegativeSpaceBoundary(
                persona_id=persona_id,
                dimension="Weekend Work",
                pattern="Rarely or never works on weekends",
                evidence=f"Only {len(weekend_activities)}/{len(timestamps)} weekend activities",
                evidence_count=len(timestamps),
                confidence=1 - (len(weekend_activities) / max(1, len(timestamps) * 0.1)),
                risk_level=BoundaryRiskLevel.LOW,
                category=BoundaryCategory.TEMPORAL.value,
                is_guardrail=False,
                tags=["weekend", "work-life-balance"]
            ))
        
        # After-hours activity analysis
        after_hours = [
            t for t in timestamps
            if t.hour < 7 or t.hour > 19
        ]
        
        if len(after_hours) < len(timestamps) * 0.1:  # Less than 10% after-hours
            boundaries.append(NegativeSpaceBoundary(
                persona_id=persona_id,
                dimension="After Hours Work",
                pattern="Rarely works outside business hours (7 AM - 7 PM)",
                evidence=f"Only {len(after_hours)}/{len(timestamps)} after-hours activities",
                evidence_count=len(timestamps),
                confidence=1 - (len(after_hours) / max(1, len(timestamps) * 0.15)),
                risk_level=BoundaryRiskLevel.LOW,
                category=BoundaryCategory.TEMPORAL.value,
                is_guardrail=False,
                tags=["after-hours", "work-life-balance"]
            ))
        
        # Friday afternoon pattern
        friday_pm = [
            t for t in timestamps
            if t.weekday() == 4 and t.hour >= 15  # Friday after 3 PM
        ]
        
        if friday_pm:
            # Check for deferred activities
            friday_pm_activities = [
                d for d in activity_data
                if "timestamp" in d and
                datetime.fromisoformat(d["timestamp"]).weekday() == 4 and
                datetime.fromisoformat(d["timestamp"]).hour >= 15
            ]
            
            deferred = sum(1 for d in friday_pm_activities if d.get("deferred", False))
            if deferred > len(friday_pm_activities) * 0.7:  # 70% deferred
                boundaries.append(NegativeSpaceBoundary(
                    persona_id=persona_id,
                    dimension="Friday PM Requests",
                    pattern="Defers most Friday afternoon requests to next week",
                    evidence=f"{deferred}/{len(friday_pm_activities)} Friday PM requests deferred",
                    evidence_count=len(friday_pm_activities),
                    confidence=deferred / max(1, len(friday_pm_activities)),
                    risk_level=BoundaryRiskLevel.MINIMAL,
                    category=BoundaryCategory.TEMPORAL.value,
                    is_guardrail=False,
                    tags=["friday", "deferred", "weekend-prep"]
                ))
        
        return boundaries
    
    def _extract_technical_boundaries(
        self,
        persona_id: str,
        activity_data: List[Dict],
        min_evidence: int
    ) -> List[NegativeSpaceBoundary]:
        """Extract technology/tool-based boundaries"""
        boundaries = []
        
        # Collect all activities with technical context
        technical_activities = [
            d for d in activity_data
            if d.get("category") == "technical" or d.get("tools_used")
        ]
        
        if len(technical_activities) < min_evidence:
            return boundaries
        
        # Production system access
        production_access = [
            d for d in technical_activities
            if any(re.search(self.technical_patterns["production"], str(v), re.I)
                  for v in d.values() if isinstance(v, str))
        ]
        
        if not production_access:
            boundaries.append(NegativeSpaceBoundary(
                persona_id=persona_id,
                dimension="Production System Access",
                pattern="Never directly accesses or modifies production systems",
                evidence=f"0/{len(technical_activities)} technical activities involve production",
                evidence_count=len(technical_activities),
                confidence=0.9,
                risk_level=BoundaryRiskLevel.HIGH,
                category=BoundaryCategory.TECHNICAL.value,
                is_guardrail=True,
                tags=["production", "safety", "critical-systems"]
            ))
        
        # Database operations
        db_operations = [
            d for d in technical_activities
            if any(re.search(self.technical_patterns["database"], str(v), re.I)
                  for v in d.values() if isinstance(v, str))
        ]
        
        if db_operations:
            # Check for write operations
            write_ops = [
                d for d in db_operations
                if any(keyword in str(d).lower() 
                      for keyword in ["update", "delete", "insert", "alter", "drop"])
            ]
            
            if not write_ops:
                boundaries.append(NegativeSpaceBoundary(
                    persona_id=persona_id,
                    dimension="Database Write Operations",
                    pattern="Only performs read operations on databases",
                    evidence=f"0/{len(db_operations)} database operations are writes",
                    evidence_count=len(db_operations),
                    confidence=0.8,
                    risk_level=BoundaryRiskLevel.MEDIUM,
                    category=BoundaryCategory.TECHNICAL.value,
                    is_guardrail=False,
                    tags=["database", "read-only", "safety"]
                ))
        
        # Tool usage patterns
        all_tools = []
        for d in technical_activities:
            if d.get("tools_used"):
                all_tools.extend(d["tools_used"])
        
        unique_tools = set(all_tools)
        
        # Identify never-used tool categories
        common_tools = {
            "version_control": ["git", "svn", "mercurial"],
            "deployment": ["jenkins", "docker", "kubernetes", "ansible"],
            "monitoring": ["datadog", "newrelic", "splunk", "grafana"],
            "scripting": ["python", "bash", "powershell", "perl"]
        }
        
        for category, tools in common_tools.items():
            if not any(tool in str(all_tools).lower() for tool in tools):
                boundaries.append(NegativeSpaceBoundary(
                    persona_id=persona_id,
                    dimension=f"{category.title()} Tools",
                    pattern=f"Never uses {category.replace('_', ' ')} tools",
                    evidence=f"None of {tools} found in {len(unique_tools)} unique tools used",
                    evidence_count=len(all_tools),
                    confidence=0.7,
                    risk_level=BoundaryRiskLevel.LOW,
                    category=BoundaryCategory.TECHNICAL.value,
                    is_guardrail=False,
                    tags=[category, "tools", "technical-stack"]
                ))
        
        return boundaries
    
    def _extract_social_boundaries(
        self,
        persona_id: str,
        activity_data: List[Dict],
        min_evidence: int
    ) -> List[NegativeSpaceBoundary]:
        """Extract interpersonal/communication boundaries"""
        boundaries = []
        
        # Collect communication activities
        comm_activities = [
            d for d in activity_data
            if d.get("category") == "communication" or d.get("recipients")
        ]
        
        if len(comm_activities) < min_evidence:
            return boundaries
        
        # Executive communication
        exec_comm = [
            d for d in comm_activities
            if any(re.search(self.social_patterns["executive"], str(v), re.I)
                  for v in d.values() if isinstance(v, str))
        ]
        
        if not exec_comm:
            boundaries.append(NegativeSpaceBoundary(
                persona_id=persona_id,
                dimension="Executive Communication",
                pattern="Never directly communicates with C-level executives",
                evidence=f"0/{len(comm_activities)} communications involve executives",
                evidence_count=len(comm_activities),
                confidence=0.85,
                risk_level=BoundaryRiskLevel.MEDIUM,
                category=BoundaryCategory.SOCIAL.value,
                is_guardrail=False,
                tags=["executive", "hierarchy", "communication"]
            ))
        
        # Customer interaction
        customer_comm = [
            d for d in comm_activities
            if any(re.search(self.social_patterns["customer"], str(v), re.I)
                  for v in d.values() if isinstance(v, str))
        ]
        
        if len(customer_comm) < len(comm_activities) * 0.05:
            boundaries.append(NegativeSpaceBoundary(
                persona_id=persona_id,
                dimension="Customer Communication",
                pattern="Rarely or never directly communicates with customers",
                evidence=f"Only {len(customer_comm)}/{len(comm_activities)} involve customers",
                evidence_count=len(comm_activities),
                confidence=0.8,
                risk_level=BoundaryRiskLevel.MEDIUM,
                category=BoundaryCategory.SOCIAL.value,
                is_guardrail=False,
                tags=["customer", "external", "communication"]
            ))
        
        # Communication channels
        channels = defaultdict(int)
        for d in comm_activities:
            if d.get("channel"):
                channels[d["channel"]] += 1
        
        # Identify never-used channels
        common_channels = ["email", "slack", "teams", "phone", "video", "in-person"]
        for channel in common_channels:
            if channel not in channels:
                boundaries.append(NegativeSpaceBoundary(
                    persona_id=persona_id,
                    dimension=f"{channel.title()} Communication",
                    pattern=f"Never uses {channel} for communication",
                    evidence=f"{channel} not found in {len(channels)} communication channels",
                    evidence_count=sum(channels.values()),
                    confidence=0.7,
                    risk_level=BoundaryRiskLevel.LOW,
                    category=BoundaryCategory.SOCIAL.value,
                    is_guardrail=False,
                    tags=[channel, "communication", "channels"]
                ))
        
        return boundaries
    
    def _extract_process_boundaries(
        self,
        persona_id: str,
        activity_data: List[Dict],
        min_evidence: int
    ) -> List[NegativeSpaceBoundary]:
        """Extract workflow/process boundaries"""
        boundaries = []
        
        # Analyze decision patterns
        decisions = [
            d for d in activity_data
            if d.get("category") == "decision" or d.get("decision_made")
        ]
        
        if len(decisions) >= min_evidence:
            # Solo vs collaborative decisions
            solo_decisions = [d for d in decisions if d.get("made_alone", False)]
            
            if len(solo_decisions) < len(decisions) * 0.1:
                boundaries.append(NegativeSpaceBoundary(
                    persona_id=persona_id,
                    dimension="Solo Decision Making",
                    pattern="Rarely makes decisions without consultation",
                    evidence=f"Only {len(solo_decisions)}/{len(decisions)} decisions made alone",
                    evidence_count=len(decisions),
                    confidence=0.85,
                    risk_level=BoundaryRiskLevel.MEDIUM,
                    category=BoundaryCategory.PROCESS.value,
                    is_guardrail=False,
                    tags=["decisions", "collaboration", "autonomy"]
                ))
            
            # Financial decisions
            financial_decisions = [
                d for d in decisions
                if any(keyword in str(d).lower() 
                      for keyword in ["budget", "cost", "expense", "invoice", "payment", "billing"])
            ]
            
            if not financial_decisions:
                boundaries.append(NegativeSpaceBoundary(
                    persona_id=persona_id,
                    dimension="Financial Decisions",
                    pattern="Never makes financial or budgetary decisions",
                    evidence=f"0/{len(decisions)} decisions involve financial matters",
                    evidence_count=len(decisions),
                    confidence=0.9,
                    risk_level=BoundaryRiskLevel.HIGH,
                    category=BoundaryCategory.FINANCIAL.value,
                    is_guardrail=True,
                    tags=["finance", "budget", "decisions"]
                ))
        
        # Documentation patterns
        documented_activities = [
            d for d in activity_data
            if d.get("documented", False) or d.get("documentation")
        ]
        
        if len(documented_activities) > len(activity_data) * 0.8:
            boundaries.append(NegativeSpaceBoundary(
                persona_id=persona_id,
                dimension="Skip Documentation",
                pattern="Always documents activities - never skips documentation",
                evidence=f"{len(documented_activities)}/{len(activity_data)} activities documented",
                evidence_count=len(activity_data),
                confidence=0.8,
                risk_level=BoundaryRiskLevel.LOW,
                category=BoundaryCategory.PROCESS.value,
                is_guardrail=False,
                tags=["documentation", "process", "compliance"]
            ))
        
        # Approval patterns
        requiring_approval = [
            d for d in activity_data
            if d.get("required_approval", False) or d.get("approval_sought", False)
        ]
        
        if len(requiring_approval) > len(activity_data) * 0.6:
            boundaries.append(NegativeSpaceBoundary(
                persona_id=persona_id,
                dimension="Independent Action",
                pattern="Frequently seeks approval before taking action",
                evidence=f"{len(requiring_approval)}/{len(activity_data)} activities required approval",
                evidence_count=len(activity_data),
                confidence=0.75,
                risk_level=BoundaryRiskLevel.MEDIUM,
                category=BoundaryCategory.AUTHORITY.value,
                is_guardrail=False,
                tags=["approval", "authority", "autonomy"]
            ))
        
        return boundaries
    
    def _check_single_boundary(
        self,
        boundary: NegativeSpaceBoundary,
        task: DelegatedTask,
        context: Dict[str, Any]
    ) -> BoundaryCheck:
        """Check if a single boundary is violated"""
        
        violated = False
        severity = 0.0
        distance = 1.0  # Default: far from boundary
        evidence = []
        recommendation = "Task is within behavioral boundaries"
        
        # Convert task and context to searchable text
        task_text = f"{task.task_type} {task.task_description} {json.dumps(task.input_data)}"
        context_text = json.dumps(context)
        combined_text = f"{task_text} {context_text}".lower()
        
        # Check based on boundary category
        if boundary.category == BoundaryCategory.TEMPORAL.value:
            # Check temporal boundaries
            current_time = context.get("current_time", datetime.utcnow())
            
            if "weekend" in boundary.dimension.lower():
                if current_time.weekday() in [5, 6]:
                    violated = True
                    severity = 0.7
                    evidence.append(f"Task scheduled for {current_time.strftime('%A')}")
                    recommendation = "Defer task to weekday"
            
            elif "after hours" in boundary.dimension.lower():
                if current_time.hour < 7 or current_time.hour > 19:
                    violated = True
                    severity = 0.6
                    evidence.append(f"Task scheduled for {current_time.strftime('%I:%M %p')}")
                    recommendation = "Schedule during business hours"
            
            elif "friday pm" in boundary.dimension.lower():
                if current_time.weekday() == 4 and current_time.hour >= 15:
                    violated = True
                    severity = 0.4
                    evidence.append("Task scheduled for Friday afternoon")
                    recommendation = "Consider deferring to Monday"
        
        elif boundary.category == BoundaryCategory.TECHNICAL.value:
            # Check technical boundaries
            if "production" in boundary.dimension.lower():
                if any(word in combined_text for word in ["production", "prod", "live"]):
                    violated = True
                    severity = 0.9
                    evidence.append("Task involves production system")
                    recommendation = "Requires elevated permissions and approval"
            
            elif "database" in boundary.dimension.lower():
                if any(word in combined_text for word in ["update", "delete", "alter", "drop"]):
                    violated = True
                    severity = 0.8
                    evidence.append("Task involves database write operations")
                    recommendation = "Consider read-only alternatives or escalation"
        
        elif boundary.category == BoundaryCategory.SOCIAL.value:
            # Check social boundaries
            if "executive" in boundary.dimension.lower():
                if any(word in combined_text for word in ["ceo", "cto", "cfo", "executive", "c-level"]):
                    violated = True
                    severity = 0.7
                    evidence.append("Task involves executive communication")
                    recommendation = "Route through appropriate channels"
            
            elif "customer" in boundary.dimension.lower():
                if any(word in combined_text for word in ["customer", "client", "user"]):
                    violated = True
                    severity = 0.6
                    evidence.append("Task involves customer interaction")
                    recommendation = "Escalate to customer-facing team"
        
        elif boundary.category == BoundaryCategory.FINANCIAL.value:
            # Check financial boundaries
            if any(word in combined_text for word in ["budget", "payment", "invoice", "expense", "cost"]):
                violated = True
                severity = 0.85
                evidence.append("Task involves financial matters")
                recommendation = "Requires financial approval"
        
        # Calculate distance to boundary (for near-miss detection)
        if not violated:
            # Use confidence and pattern matching to estimate distance
            pattern_matches = sum(1 for word in boundary.pattern.lower().split()
                                if word in combined_text)
            distance = 1 - (pattern_matches / max(1, len(boundary.pattern.split())))
        else:
            distance = 0
        
        return BoundaryCheck(
            boundary_id=str(boundary.id),
            violated=violated,
            severity=severity * boundary.impact_score,  # Adjust by impact
            distance_to_boundary=distance,
            recommendation=recommendation,
            evidence=evidence
        )
    
    def _record_violation(
        self,
        boundary_id: str,
        task_id: str,
        check: BoundaryCheck
    ):
        """Record a boundary violation or near-miss"""
        try:
            with get_db() as db:
                violation = BoundaryViolation(
                    boundary_id=boundary_id,
                    task_id=task_id,
                    violation_type="violation" if check.violated else "near_miss",
                    severity=check.severity,
                    description=check.recommendation,
                    context_data={
                        "evidence": check.evidence,
                        "distance": check.distance_to_boundary
                    }
                )
                db.add(violation)
                
                # Update boundary violation count
                boundary = db.query(NegativeSpaceBoundary).filter(
                    NegativeSpaceBoundary.id == boundary_id
                ).first()
                
                if boundary:
                    if check.violated:
                        boundary.violation_count += 1
                        boundary.last_violation = datetime.utcnow()
                    else:
                        boundary.near_miss_count += 1
                
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to record violation: {str(e)}")
    
    def _store_boundaries(self, boundaries: List[NegativeSpaceBoundary]):
        """Store extracted boundaries in database"""
        try:
            with get_db() as db:
                for boundary in boundaries:
                    # Check if similar boundary exists
                    existing = db.query(NegativeSpaceBoundary).filter(
                        NegativeSpaceBoundary.persona_id == boundary.persona_id,
                        NegativeSpaceBoundary.dimension == boundary.dimension
                    ).first()
                    
                    if existing:
                        # Update existing boundary
                        existing.pattern = boundary.pattern
                        existing.evidence = boundary.evidence
                        existing.evidence_count = boundary.evidence_count
                        existing.confidence = boundary.confidence
                        existing.updated_at = datetime.utcnow()
                    else:
                        # Add new boundary
                        db.add(boundary)
                
                db.commit()
                logger.info(f"Stored {len(boundaries)} boundaries")
                
        except Exception as e:
            logger.error(f"Failed to store boundaries: {str(e)}")
            raise

# Export main analyzer class
__all__ = ["NegativeSpaceAnalyzer", "BoundaryCategory", "BoundaryCheck"]