"""
BDT Phase 3 Database Models
SQLAlchemy models for the Guided Twin implementation
"""

from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, Boolean, ForeignKey, Text, Enum, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

# Enums
class CapabilityLevel(enum.Enum):
    L1_BASIC = "L1"
    L2_MIMIC = "L2"
    L3_GUIDED = "L3"
    L4_DELEGATED = "L4"

class ApprovalStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    ESCALATED = "escalated"
    EXPIRED = "expired"

class RiskLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class PersonaType(enum.Enum):
    INDIVIDUAL = "individual"
    GROUP = "group"
    COMPARATIVE = "comparative"

# Main Models
class PersonaModel(Base):
    """Core persona model with Fourth Ontology scores"""
    __tablename__ = "personas"
    
    id = Column(Integer, primary_key=True)
    user_email = Column(String(255), unique=True, index=True)
    display_name = Column(String(255))
    persona_type = Column(Enum(PersonaType), default=PersonaType.INDIVIDUAL)
    capability_level = Column(Enum(CapabilityLevel), default=CapabilityLevel.L1_BASIC)
    
    # Fourth Ontology scores (0-1 scale)
    decision_score = Column(Float, default=0.5)
    power_score = Column(Float, default=0.5)
    fear_score = Column(Float, default=0.5)
    reward_score = Column(Float, default=0.5)
    meaning_score = Column(Float, default=0.5)
    
    # Five Core Behavioral Dimensions
    communication_patterns = Column(JSON, default={})
    decision_patterns = Column(JSON, default={})
    problem_solving_patterns = Column(JSON, default={})
    tool_patterns = Column(JSON, default={})
    temporal_patterns = Column(JSON, default={})
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync = Column(DateTime, nullable=True)
    data_sources = Column(JSON, default=[])
    total_documents = Column(Integer, default=0)
    
    # Relationships
    negative_spaces = relationship("NegativeSpace", back_populates="persona", cascade="all, delete-orphan")
    hilt_actions = relationship("HILTAction", back_populates="persona", cascade="all, delete-orphan")
    ontology_adjustments = relationship("OntologyAdjustment", back_populates="persona", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="persona", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_persona_email', 'user_email'),
        Index('idx_persona_capability', 'capability_level'),
    )

class NegativeSpace(Base):
    """Behavioral boundaries - what the persona DOESN'T do"""
    __tablename__ = "negative_spaces"
    
    id = Column(Integer, primary_key=True)
    persona_id = Column(Integer, ForeignKey("personas.id", ondelete="CASCADE"))
    
    category = Column(String(50))  # tasks, tools, times, decisions
    pattern = Column(Text)
    description = Column(Text, nullable=True)
    
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.MEDIUM)
    evidence_count = Column(Integer, default=0)
    confidence = Column(Float, default=0.5)
    
    is_active = Column(Boolean, default=True)
    override_allowed = Column(Boolean, default=True)
    
    # Violation tracking
    violation_count = Column(Integer, default=0)
    last_violated = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    persona = relationship("PersonaModel", back_populates="negative_spaces")
    
    # Indexes
    __table_args__ = (
        Index('idx_ns_persona', 'persona_id'),
        Index('idx_ns_category', 'category'),
        Index('idx_ns_active', 'is_active'),
    )

class HILTAction(Base):
    """Human-in-the-Loop action tracking"""
    __tablename__ = "hilt_actions"
    
    id = Column(Integer, primary_key=True)
    persona_id = Column(Integer, ForeignKey("personas.id", ondelete="CASCADE"))
    
    # Action details
    action_type = Column(String(50))
    action_payload = Column(JSON)
    original_query = Column(Text)
    context = Column(JSON, nullable=True)
    
    # Risk and confidence
    confidence_score = Column(Float)
    risk_score = Column(Float)
    risk_level = Column(Enum(RiskLevel))
    risk_factors = Column(JSON, nullable=True)
    
    # Approval workflow
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING, index=True)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    modified_payload = Column(JSON, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Escalation
    escalated = Column(Boolean, default=False)
    escalation_reason = Column(Text, nullable=True)
    escalated_to = Column(String(255), nullable=True)
    escalated_at = Column(DateTime, nullable=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime)
    executed_at = Column(DateTime, nullable=True)
    response_time_seconds = Column(Float, nullable=True)
    
    # Results
    execution_result = Column(JSON, nullable=True)
    execution_error = Column(Text, nullable=True)
    execution_success = Column(Boolean, nullable=True)
    
    # Relationships
    persona = relationship("PersonaModel", back_populates="hilt_actions")
    
    # Indexes
    __table_args__ = (
        Index('idx_hilt_persona', 'persona_id'),
        Index('idx_hilt_status', 'status'),
        Index('idx_hilt_created', 'created_at'),
        Index('idx_hilt_risk', 'risk_level'),
    )

class OntologyAdjustment(Base):
    """Track Fourth Ontology dimension adjustments"""
    __tablename__ = "ontology_adjustments"
    
    id = Column(Integer, primary_key=True)
    persona_id = Column(Integer, ForeignKey("personas.id", ondelete="CASCADE"))
    
    dimension = Column(String(20))  # decision, power, fear, reward, meaning
    previous_value = Column(Float)
    new_value = Column(Float)
    delta = Column(Float)
    
    adjustment_reason = Column(Text)
    adjusted_by = Column(String(255))
    adjusted_at = Column(DateTime, default=datetime.utcnow)
    
    # Impact analysis
    affected_boundaries = Column(JSON, nullable=True)
    projected_impact = Column(JSON, nullable=True)
    actual_impact = Column(JSON, nullable=True)
    
    # Validation
    validated = Column(Boolean, default=False)
    validation_date = Column(DateTime, nullable=True)
    validation_notes = Column(Text, nullable=True)
    
    # Relationships
    persona = relationship("PersonaModel", back_populates="ontology_adjustments")
    
    # Indexes
    __table_args__ = (
        Index('idx_ont_persona', 'persona_id'),
        Index('idx_ont_dimension', 'dimension'),
        Index('idx_ont_date', 'adjusted_at'),
    )

class AuditLog(Base):
    """Comprehensive audit logging for compliance"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    persona_id = Column(Integer, ForeignKey("personas.id", ondelete="CASCADE"), nullable=True)
    action_id = Column(Integer, ForeignKey("hilt_actions.id", ondelete="CASCADE"), nullable=True)
    
    event_type = Column(String(50), index=True)
    event_category = Column(String(50))
    event_data = Column(JSON)
    
    user_email = Column(String(255), index=True)
    ip_address = Column(String(45))
    user_agent = Column(Text, nullable=True)
    session_id = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    persona = relationship("PersonaModel", back_populates="audit_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_persona', 'persona_id'),
        Index('idx_audit_user', 'user_email'),
        Index('idx_audit_event', 'event_type'),
        Index('idx_audit_created', 'created_at'),
    )

class BehavioralPattern(Base):
    """Store extracted behavioral patterns"""
    __tablename__ = "behavioral_patterns"
    
    id = Column(Integer, primary_key=True)
    persona_id = Column(Integer, ForeignKey("personas.id", ondelete="CASCADE"))
    
    pattern_type = Column(String(50))  # communication, decision, problem_solving, tool_usage, temporal
    pattern_name = Column(String(100))
    pattern_value = Column(JSON)
    
    frequency = Column(Float, default=0.0)
    confidence = Column(Float, default=0.5)
    evidence_count = Column(Integer, default=0)
    
    first_observed = Column(DateTime, default=datetime.utcnow)
    last_observed = Column(DateTime, default=datetime.utcnow)
    
    # Metadata
    source_documents = Column(JSON, nullable=True)
    extraction_method = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_pattern_persona', 'persona_id'),
        Index('idx_pattern_type', 'pattern_type'),
        Index('idx_pattern_confidence', 'confidence'),
    )

class DocumentIngestion(Base):
    """Track document ingestion status"""
    __tablename__ = "document_ingestion"
    
    id = Column(Integer, primary_key=True)
    persona_id = Column(Integer, ForeignKey("personas.id", ondelete="CASCADE"))
    
    source_type = Column(String(50))  # email, calendar, document, chat
    source_id = Column(String(255), unique=True)
    
    document_metadata = Column(JSON)
    content_hash = Column(String(64))
    
    ingested_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)
    
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Statistics
    chunk_count = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    
    # Indexes
    __table_args__ = (
        Index('idx_doc_persona', 'persona_id'),
        Index('idx_doc_source', 'source_type'),
        Index('idx_doc_processed', 'processed'),
        Index('idx_doc_source_id', 'source_id'),
    )

class SystemMetrics(Base):
    """Track system performance metrics"""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True)
    
    metric_type = Column(String(50))
    metric_name = Column(String(100))
    metric_value = Column(Float)
    metric_unit = Column(String(20))
    
    metadata = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_metrics_type', 'metric_type'),
        Index('idx_metrics_timestamp', 'timestamp'),
    )

# Create all tables function
def create_all_tables(engine):
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

# Drop all tables function (use with caution)
def drop_all_tables(engine):
    """Drop all database tables - USE WITH CAUTION"""
    Base.metadata.drop_all(bind=engine)
