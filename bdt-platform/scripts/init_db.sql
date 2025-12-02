-- BDT Platform Database Initialization Script
-- Creates all necessary databases, schemas, and initial data

-- Create databases
CREATE DATABASE IF NOT EXISTS bdt_poc;
CREATE DATABASE IF NOT EXISTS bdt_security;
CREATE DATABASE IF NOT EXISTS bdt_monitoring;

-- Switch to main database
\c bdt_poc;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS ingestion;
CREATE SCHEMA IF NOT EXISTS processing;
CREATE SCHEMA IF NOT EXISTS analysis;
CREATE SCHEMA IF NOT EXISTS personas;

-- Main Personas table
CREATE TABLE IF NOT EXISTS personas.personas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) DEFAULT 'individual',
    status VARCHAR(50) DEFAULT 'initializing',
    capability_level INTEGER DEFAULT 1,
    
    -- Fourth Ontology scores
    decision_score FLOAT DEFAULT 50.0,
    power_score FLOAT DEFAULT 50.0,
    fear_score FLOAT DEFAULT 50.0,
    reward_score FLOAT DEFAULT 50.0,
    meaning_score FLOAT DEFAULT 50.0,
    
    -- Metadata
    data_sources JSONB DEFAULT '[]'::jsonb,
    patterns_extracted JSONB DEFAULT '{}'::jsonb,
    negative_space JSONB DEFAULT '{}'::jsonb,
    settings JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_personas_user_id (user_id),
    INDEX idx_personas_status (status),
    INDEX idx_personas_type (type)
);

-- Documents table for ingested content
CREATE TABLE IF NOT EXISTS ingestion.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID REFERENCES personas.personas(id) ON DELETE CASCADE,
    source_id VARCHAR(500) UNIQUE NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- email, calendar, file, teams
    
    -- Content
    title TEXT,
    content TEXT,
    content_hash VARCHAR(64),
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Processing status
    processing_status VARCHAR(50) DEFAULT 'pending',
    embedded BOOLEAN DEFAULT FALSE,
    patterns_extracted BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    document_date TIMESTAMP,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    
    -- Full text search
    search_vector tsvector,
    
    -- Indexes
    INDEX idx_documents_persona_id (persona_id),
    INDEX idx_documents_source_type (source_type),
    INDEX idx_documents_processing_status (processing_status),
    INDEX idx_documents_document_date (document_date DESC),
    INDEX idx_documents_search_vector USING gin(search_vector),
    INDEX idx_documents_metadata USING gin(metadata)
);

-- Trigger to update search vector
CREATE OR REPLACE FUNCTION update_search_vector() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER documents_search_vector_update
    BEFORE INSERT OR UPDATE ON ingestion.documents
    FOR EACH ROW
    EXECUTE FUNCTION update_search_vector();

-- Chunks table for vector embeddings
CREATE TABLE IF NOT EXISTS processing.chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES ingestion.documents(id) ON DELETE CASCADE,
    persona_id UUID REFERENCES personas.personas(id) ON DELETE CASCADE,
    
    -- Content
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_hash VARCHAR(64),
    
    -- Embedding data
    embedding_id VARCHAR(255),
    embedding_model VARCHAR(100),
    embedding_dimensions INTEGER,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_chunks_document_id (document_id),
    INDEX idx_chunks_persona_id (persona_id),
    INDEX idx_chunks_embedding_id (embedding_id),
    UNIQUE(document_id, chunk_index)
);

-- Behavioral patterns table
CREATE TABLE IF NOT EXISTS analysis.behavioral_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID REFERENCES personas.personas(id) ON DELETE CASCADE,
    
    -- Pattern details
    pattern_type VARCHAR(100) NOT NULL,
    pattern_name VARCHAR(255) NOT NULL,
    pattern_value JSONB NOT NULL,
    confidence_score FLOAT,
    
    -- Evidence
    evidence_count INTEGER DEFAULT 0,
    evidence_documents JSONB DEFAULT '[]'::jsonb,
    
    -- Timestamps
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_patterns_persona_id (persona_id),
    INDEX idx_patterns_type (pattern_type),
    INDEX idx_patterns_confidence (confidence_score DESC)
);

-- Communication patterns
CREATE TABLE IF NOT EXISTS analysis.communication_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID REFERENCES personas.personas(id) ON DELETE CASCADE,
    
    -- Response metrics
    avg_response_time_minutes FLOAT,
    median_response_time_minutes FLOAT,
    response_time_variance FLOAT,
    
    -- Message characteristics
    avg_message_length INTEGER,
    preferred_greeting_style VARCHAR(100),
    preferred_closing_style VARCHAR(100),
    formality_score FLOAT,
    
    -- Channel preferences
    email_percentage FLOAT,
    chat_percentage FLOAT,
    meeting_percentage FLOAT,
    
    -- Temporal patterns
    most_active_hour INTEGER,
    most_active_day VARCHAR(20),
    weekend_activity_ratio FLOAT,
    
    -- Metadata
    sample_size INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_comm_patterns_persona_id (persona_id),
    UNIQUE(persona_id)
);

-- Decision patterns
CREATE TABLE IF NOT EXISTS analysis.decision_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID REFERENCES personas.personas(id) ON DELETE CASCADE,
    
    -- Decision metrics
    avg_decision_time_hours FLOAT,
    data_requirements_score FLOAT, -- 0-100, higher = more data needed
    consensus_seeking_score FLOAT, -- 0-100, higher = more collaborative
    risk_tolerance_score FLOAT, -- 0-100, higher = more risk tolerant
    
    -- Approval patterns
    self_approval_percentage FLOAT,
    escalation_frequency FLOAT,
    typical_approvers JSONB DEFAULT '[]'::jsonb,
    
    -- Metadata
    sample_size INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_decision_patterns_persona_id (persona_id),
    UNIQUE(persona_id)
);

-- Negative space boundaries
CREATE TABLE IF NOT EXISTS analysis.negative_space (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID REFERENCES personas.personas(id) ON DELETE CASCADE,
    
    -- Boundary details
    boundary_type VARCHAR(100) NOT NULL, -- temporal, technical, social, process
    boundary_name VARCHAR(255) NOT NULL,
    boundary_rule TEXT NOT NULL,
    
    -- Risk assessment
    risk_level VARCHAR(20) NOT NULL, -- low, medium, high, critical
    can_override BOOLEAN DEFAULT TRUE,
    
    -- Evidence
    evidence_count INTEGER DEFAULT 1,
    last_violated TIMESTAMP,
    
    -- Timestamps
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_negative_space_persona_id (persona_id),
    INDEX idx_negative_space_type (boundary_type),
    INDEX idx_negative_space_risk (risk_level)
);

-- Ingestion jobs tracking
CREATE TABLE IF NOT EXISTS ingestion.jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID REFERENCES personas.personas(id) ON DELETE CASCADE,
    source VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    progress FLOAT DEFAULT 0.0,
    
    -- Metrics
    documents_processed INTEGER DEFAULT 0,
    documents_failed INTEGER DEFAULT 0,
    bytes_processed BIGINT DEFAULT 0,
    
    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    estimated_completion TIMESTAMP,
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Metadata
    config JSONB DEFAULT '{}'::jsonb,
    
    -- Indexes
    INDEX idx_jobs_persona_id (persona_id),
    INDEX idx_jobs_status (status),
    INDEX idx_jobs_started_at (started_at DESC)
);

-- Query history
CREATE TABLE IF NOT EXISTS analysis.queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID REFERENCES personas.personas(id) ON DELETE CASCADE,
    
    -- Query details
    question TEXT NOT NULL,
    answer TEXT,
    query_type VARCHAR(50), -- factual, behavioral, predictive
    
    -- Quality metrics
    confidence_score FLOAT,
    response_time_ms INTEGER,
    tokens_used INTEGER,
    
    -- Evidence
    evidence JSONB DEFAULT '[]'::jsonb,
    sources_used JSONB DEFAULT '[]'::jsonb,
    
    -- User feedback
    user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),
    user_feedback TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_queries_persona_id (persona_id),
    INDEX idx_queries_created_at (created_at DESC),
    INDEX idx_queries_type (query_type)
);

-- HILT actions tracking
CREATE TABLE IF NOT EXISTS analysis.hilt_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    persona_id UUID REFERENCES personas.personas(id) ON DELETE CASCADE,
    
    -- Action details
    action_type VARCHAR(100) NOT NULL,
    action_description TEXT,
    proposed_action JSONB NOT NULL,
    
    -- Risk assessment
    confidence_score FLOAT,
    risk_score FLOAT,
    requires_approval BOOLEAN DEFAULT TRUE,
    
    -- Approval workflow
    status VARCHAR(50) DEFAULT 'pending', -- pending, approved, rejected, executed
    approved_by VARCHAR(255),
    approval_notes TEXT,
    executed_action JSONB,
    
    -- Timestamps
    proposed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP,
    executed_at TIMESTAMP,
    
    -- Indexes
    INDEX idx_hilt_persona_id (persona_id),
    INDEX idx_hilt_status (status),
    INDEX idx_hilt_proposed_at (proposed_at DESC)
);

-- Performance metrics
CREATE TABLE IF NOT EXISTS monitoring.performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    
    -- Dimensions
    labels JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamp
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_metrics_service (service_name),
    INDEX idx_metrics_name (metric_name),
    INDEX idx_metrics_recorded (recorded_at DESC),
    INDEX idx_metrics_labels USING gin(labels)
);

-- Create materialized view for persona statistics
CREATE MATERIALIZED VIEW personas.statistics AS
SELECT 
    p.id as persona_id,
    p.name,
    p.capability_level,
    COUNT(DISTINCT d.id) as total_documents,
    COUNT(DISTINCT c.id) as total_chunks,
    COUNT(DISTINCT bp.id) as total_patterns,
    COUNT(DISTINCT ns.id) as total_boundaries,
    COUNT(DISTINCT q.id) as total_queries,
    AVG(q.confidence_score) as avg_query_confidence,
    AVG(q.response_time_ms) as avg_response_time_ms,
    MAX(d.ingested_at) as last_ingestion,
    MAX(q.created_at) as last_query
FROM personas.personas p
LEFT JOIN ingestion.documents d ON p.id = d.persona_id
LEFT JOIN processing.chunks c ON p.id = c.persona_id
LEFT JOIN analysis.behavioral_patterns bp ON p.id = bp.persona_id
LEFT JOIN analysis.negative_space ns ON p.id = ns.persona_id
LEFT JOIN analysis.queries q ON p.id = q.persona_id
GROUP BY p.id, p.name, p.capability_level;

-- Create index on materialized view
CREATE UNIQUE INDEX idx_statistics_persona_id ON personas.statistics(persona_id);

-- Function to refresh statistics
CREATE OR REPLACE FUNCTION refresh_persona_statistics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY personas.statistics;
END;
$$ LANGUAGE plpgsql;

-- Switch to security database
\c bdt_security;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create security schema
CREATE SCHEMA IF NOT EXISTS auth;

-- (Security tables will be created by security_service.py migrations)

-- Switch to monitoring database
\c bdt_monitoring;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb" CASCADE;

-- Create monitoring schema
CREATE SCHEMA IF NOT EXISTS metrics;

-- (Monitoring tables will be created by monitoring_service.py migrations)

-- Create hypertable for time-series data
-- SELECT create_hypertable('monitoring.performance_metrics', 'recorded_at', if_not_exists => TRUE);

-- Grant permissions
\c bdt_poc;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA personas TO bdt;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ingestion TO bdt;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA processing TO bdt;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analysis TO bdt;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA personas TO bdt;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ingestion TO bdt;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA processing TO bdt;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analysis TO bdt;

-- Create indexes for performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_composite 
    ON ingestion.documents(persona_id, source_type, document_date DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_patterns_composite 
    ON analysis.behavioral_patterns(persona_id, pattern_type, confidence_score DESC);

-- Add comments for documentation
COMMENT ON TABLE personas.personas IS 'Core persona definitions with Fourth Ontology scores';
COMMENT ON TABLE ingestion.documents IS 'All ingested documents from various sources';
COMMENT ON TABLE processing.chunks IS 'Document chunks with vector embedding references';
COMMENT ON TABLE analysis.behavioral_patterns IS 'Extracted behavioral patterns from document analysis';
COMMENT ON TABLE analysis.negative_space IS 'Boundaries defining what the persona does NOT do';

-- Final setup
\echo 'BDT Platform database initialization complete!'
\echo 'Databases created: bdt_poc, bdt_security, bdt_monitoring'
\echo 'Remember to run application-specific migrations for each service'
