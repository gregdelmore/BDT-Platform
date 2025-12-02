"""
Database models and connection management for BDT Phase 4
"""
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, 
    DateTime, JSON, Text, ForeignKey, Index, UniqueConstraint,
    Enum as SQLEnum, CheckConstraint, event
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any, List
import uuid
from datetime import datetime
from enum import Enum
import logging

from .config import settings

logger = logging.getLogger(__name__)

# Create base class for models
Base = declarative_base()

# Create engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Enums
class CapabilityLevel(str, Enum):
    L1_BASIC_QA = "L1_BASIC_QA"
    L2_BEHAVIORAL_MIMIC = "L2_BEHAVIORAL_MIMIC"
    L3_GUIDED_TWIN = "L3_GUIDED_TWIN"
    L4_DELEGATED_AGENT = "L4_DELEGATED_AGENT"

class PersonaType(str, Enum):
    INDIVIDUAL = "INDIVIDUAL"
    GROUP = "GROUP"
    HYBRID = "HYBRID"

class BoundaryRiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    MINIMAL = "MINIMAL"

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class ApprovalAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MODIFY = "MODIFY"
    DELEGATE = "DELEGATE"

# Models
class Persona(Base):
    """Digital twin persona model"""
    __tablename__ = "personas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    type = Column(SQLEnum(PersonaType), nullable=False, default=PersonaType.INDIVIDUAL)
    capability_level = Column(SQLEnum(CapabilityLevel), nullable=False, default=CapabilityLevel.L1_BASIC_QA)
    
    # Metadata
    source_user_id = Column(String(255))  # Microsoft/Google user ID
    source_email = Column(String(255))
    organization_id = Column(UUID(as_uuid=True))
    
    # Status
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime(timezone=True))
    total_documents = Column(Integer, default=0)
    total_patterns = Column(Integer, default=0)
    
    # Configuration
    config = Column(JSONB, default={})
    permissions = Column(JSONB, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    ontology = relationship("OntologyMapping", back_populates="persona", uselist=False, cascade="all, delete-orphan")
    boundaries = relationship("NegativeSpaceBoundary", back_populates="persona", cascade="all, delete-orphan")
    tasks = relationship("DelegatedTask", back_populates="persona", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="persona", cascade="all, delete-orphan")
    behavioral_patterns = relationship("BehavioralPattern", back_populates="persona", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_persona_source", "source_user_id", "organization_id"),
        Index("idx_persona_active", "is_active", "capability_level"),
    )

class OntologyMapping(Base):
    """Fourth Ontology dimension mappings for a persona"""
    __tablename__ = "ontology_mappings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, unique=True)
    
    # Ontology Dimensions (0-100 scale)
    decisions_value = Column(Float, default=50, nullable=False)
    decisions_confidence = Column(Float, default=0.5)
    decisions_evidence_count = Column(Integer, default=0)
    decisions_metadata = Column(JSONB, default={})
    
    power_value = Column(Float, default=50, nullable=False)
    power_confidence = Column(Float, default=0.5)
    power_evidence_count = Column(Integer, default=0)
    power_metadata = Column(JSONB, default={})
    
    fear_value = Column(Float, default=50, nullable=False)
    fear_confidence = Column(Float, default=0.5)
    fear_evidence_count = Column(Integer, default=0)
    fear_metadata = Column(JSONB, default={})
    
    reward_value = Column(Float, default=50, nullable=False)
    reward_confidence = Column(Float, default=0.5)
    reward_evidence_count = Column(Integer, default=0)
    reward_metadata = Column(JSONB, default={})
    
    meaning_value = Column(Float, default=50, nullable=False)
    meaning_confidence = Column(Float, default=0.5)
    meaning_evidence_count = Column(Integer, default=0)
    meaning_metadata = Column(JSONB, default={})
    
    # Adjustable parameters
    parameters = Column(JSONB, default={
        "analysis_depth": 0.7,
        "approval_threshold": 0.8,
        "autonomy_radius": 0.5,
        "escalation_sensitivity": 0.6,
        "safety_buffer": 0.9,
        "confidence_required": 0.7,
        "recognition_threshold": 0.5,
        "success_definition": 0.8,
        "significance_threshold": 0.6,
        "purpose_alignment": 0.7
    })
    
    # Learning history
    adjustment_history = Column(JSONB, default=[])
    learning_rate = Column(Float, default=0.1)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_calculated = Column(DateTime(timezone=True))
    
    # Relationships
    persona = relationship("Persona", back_populates="ontology")
    
    __table_args__ = (
        CheckConstraint("decisions_value >= 0 AND decisions_value <= 100"),
        CheckConstraint("power_value >= 0 AND power_value <= 100"),
        CheckConstraint("fear_value >= 0 AND fear_value <= 100"),
        CheckConstraint("reward_value >= 0 AND reward_value <= 100"),
        CheckConstraint("meaning_value >= 0 AND meaning_value <= 100"),
        Index("idx_ontology_persona", "persona_id"),
    )

class NegativeSpaceBoundary(Base):
    """Behavioral boundaries that should NOT be crossed"""
    __tablename__ = "negative_space_boundaries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    
    # Boundary definition
    dimension = Column(String(255), nullable=False)  # e.g., "Billing/Finance", "Friday PM Requests"
    pattern = Column(Text, nullable=False)  # Description of the boundary
    evidence = Column(Text)  # Supporting evidence for this boundary
    evidence_count = Column(Integer, default=1)
    confidence = Column(Float, default=0.5)
    
    # Risk assessment
    risk_level = Column(SQLEnum(BoundaryRiskLevel), nullable=False, default=BoundaryRiskLevel.MEDIUM)
    impact_score = Column(Float, default=0.5)  # 0-1 scale
    
    # Control settings
    is_guardrail = Column(Boolean, default=True)  # If True, cannot be disabled
    is_active = Column(Boolean, default=True)
    override_allowed = Column(Boolean, default=False)
    override_requires_approval = Column(Boolean, default=True)
    
    # Violation tracking
    violation_count = Column(Integer, default=0)
    near_miss_count = Column(Integer, default=0)
    last_violation = Column(DateTime(timezone=True))
    
    # Metadata
    category = Column(String(100))  # Temporal, Technical, Social, Process
    tags = Column(ARRAY(String))
    metadata = Column(JSONB, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    persona = relationship("Persona", back_populates="boundaries")
    violations = relationship("BoundaryViolation", back_populates="boundary", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_boundary_persona", "persona_id", "is_active"),
        Index("idx_boundary_risk", "risk_level", "is_guardrail"),
        UniqueConstraint("persona_id", "dimension", name="uq_persona_dimension"),
    )

class DelegatedTask(Base):
    """Tasks delegated to the L4 agent"""
    __tablename__ = "delegated_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    
    # Task definition
    task_type = Column(String(100), nullable=False)  # email_reply, meeting_schedule, etc.
    task_description = Column(Text, nullable=False)
    input_data = Column(JSONB, nullable=False)
    expected_output = Column(JSONB)
    
    # Execution planning
    confidence_score = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False)
    complexity_score = Column(Float)
    estimated_duration = Column(Integer)  # seconds
    
    # HILT control
    requires_approval = Column(Boolean, default=False)
    approval_status = Column(SQLEnum(ApprovalAction))
    approved_by = Column(String(255))
    approved_at = Column(DateTime(timezone=True))
    approval_notes = Column(Text)
    
    # Execution
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    execution_time = Column(Float)  # seconds
    
    # Results
    output_data = Column(JSONB)
    success = Column(Boolean)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Learning
    feedback_score = Column(Float)  # -1 to 1
    feedback_notes = Column(Text)
    patterns_learned = Column(JSONB, default=[])
    
    # Audit trail
    execution_log = Column(JSONB, default=[])
    boundary_checks = Column(JSONB, default=[])
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    persona = relationship("Persona", back_populates="tasks")
    
    __table_args__ = (
        Index("idx_task_persona_status", "persona_id", "status"),
        Index("idx_task_approval", "requires_approval", "approval_status"),
        Index("idx_task_created", "created_at"),
    )

class BehavioralPattern(Base):
    """Extracted behavioral patterns from data analysis"""
    __tablename__ = "behavioral_patterns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    
    # Pattern identification
    category = Column(String(100), nullable=False)  # communication, decision, problem_solving, etc.
    subcategory = Column(String(100))
    pattern_name = Column(String(255), nullable=False)
    pattern_description = Column(Text)
    
    # Pattern metrics
    occurrence_count = Column(Integer, default=1)
    confidence = Column(Float, default=0.5)
    strength = Column(Float, default=0.5)  # How strong/consistent is this pattern
    
    # Pattern data
    examples = Column(JSONB, default=[])  # Specific examples of this pattern
    conditions = Column(JSONB, default={})  # When does this pattern occur
    exceptions = Column(JSONB, default=[])  # When does this pattern NOT occur
    
    # Temporal aspects
    time_of_day_distribution = Column(JSONB)  # {morning: 0.3, afternoon: 0.5, evening: 0.2}
    day_of_week_distribution = Column(JSONB)
    seasonal_variation = Column(JSONB)
    
    # Relationships to other patterns
    correlated_patterns = Column(ARRAY(UUID(as_uuid=True)))
    conflicting_patterns = Column(ARRAY(UUID(as_uuid=True)))
    
    # Learning
    last_observed = Column(DateTime(timezone=True))
    trend = Column(String(20))  # increasing, decreasing, stable
    
    # Metadata
    source_documents = Column(Integer, default=0)
    metadata = Column(JSONB, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    persona = relationship("Persona", back_populates="behavioral_patterns")
    
    __table_args__ = (
        Index("idx_pattern_persona_category", "persona_id", "category"),
        Index("idx_pattern_confidence", "confidence", "strength"),
    )

class BoundaryViolation(Base):
    """Record of boundary violations or near-misses"""
    __tablename__ = "boundary_violations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    boundary_id = Column(UUID(as_uuid=True), ForeignKey("negative_space_boundaries.id"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("delegated_tasks.id"))
    
    # Violation details
    violation_type = Column(String(50), nullable=False)  # violation, near_miss, override
    severity = Column(Float, nullable=False)  # 0-1 scale
    description = Column(Text)
    
    # Context
    context_data = Column(JSONB)
    action_attempted = Column(Text)
    action_taken = Column(Text)
    
    # Resolution
    resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text)
    resolved_by = Column(String(255))
    resolved_at = Column(DateTime(timezone=True))
    
    # Learning
    pattern_updated = Column(Boolean, default=False)
    boundary_adjusted = Column(Boolean, default=False)
    
    # Timestamps
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    boundary = relationship("NegativeSpaceBoundary", back_populates="violations")
    
    __table_args__ = (
        Index("idx_violation_boundary", "boundary_id", "violation_type"),
        Index("idx_violation_time", "occurred_at"),
    )

class AuditLog(Base):
    """Comprehensive audit trail for all actions"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"))
    
    # Action details
    action_type = Column(String(100), nullable=False)
    action_category = Column(String(50))  # task, boundary, ontology, config
    action_description = Column(Text)
    
    # Actor
    actor_type = Column(String(50), nullable=False)  # agent, user, system
    actor_id = Column(String(255))
    actor_details = Column(JSONB)
    
    # Data
    before_state = Column(JSONB)
    after_state = Column(JSONB)
    changes = Column(JSONB)
    
    # Results
    success = Column(Boolean, default=True)
    error_details = Column(Text)
    
    # Metadata
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    session_id = Column(String(255))
    request_id = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    persona = relationship("Persona", back_populates="audit_logs")
    
    __table_args__ = (
        Index("idx_audit_persona_time", "persona_id", "created_at"),
        Index("idx_audit_action", "action_type", "action_category"),
        Index("idx_audit_actor", "actor_type", "actor_id"),
    )

# Database helper functions
@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Get database session with automatic cleanup"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

def reset_db():
    """Reset database (WARNING: Drops all tables)"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.warning("Database reset complete")

# Event listeners for automatic timestamp updates
@event.listens_for(Session, "before_flush")
def receive_before_flush(session, flush_context, instances):
    """Automatically update timestamps"""
    for instance in session.dirty:
        if hasattr(instance, "updated_at"):
            instance.updated_at = datetime.utcnow()

# Create tables on module import (if not exists)
if __name__ == "__main__":
    init_db()