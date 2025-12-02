"""
Configuration management for BDT Phase 4
"""
from typing import Optional, Dict, Any
from pydantic import BaseSettings, Field, validator
from functools import lru_cache
import os
from pathlib import Path

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "BDT Phase 4 - Delegated Agent"
    APP_VERSION: str = "4.0.0"
    DEBUG: bool = Field(False, env="DEBUG")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DB_POOL_SIZE: int = Field(20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(40, env="DB_MAX_OVERFLOW")
    
    # Redis
    REDIS_URL: str = Field("redis://localhost:6379", env="REDIS_URL")
    REDIS_TTL: int = Field(3600, env="REDIS_TTL")
    
    # Vector Database
    QDRANT_URL: str = Field("http://localhost:6333", env="QDRANT_URL")
    QDRANT_COLLECTION: str = Field("bdt_embeddings", env="QDRANT_COLLECTION")
    EMBEDDING_DIM: int = Field(1536, env="EMBEDDING_DIM")
    
    # OpenAI
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field("gpt-4-turbo-preview", env="OPENAI_MODEL")
    OPENAI_EMBEDDING_MODEL: str = Field("text-embedding-3-large", env="OPENAI_EMBEDDING_MODEL")
    
    # Microsoft 365
    MS_CLIENT_ID: Optional[str] = Field(None, env="MS_CLIENT_ID")
    MS_CLIENT_SECRET: Optional[str] = Field(None, env="MS_CLIENT_SECRET")
    MS_TENANT_ID: Optional[str] = Field(None, env="MS_TENANT_ID")
    MS_SCOPES: list = Field(
        default=[
            "https://graph.microsoft.com/Mail.Read",
            "https://graph.microsoft.com/Calendars.Read",
            "https://graph.microsoft.com/Files.Read.All",
            "https://graph.microsoft.com/User.Read"
        ]
    )
    
    # Fourth Ontology Parameters
    ONTOLOGY_DIMENSIONS: Dict[str, Dict[str, Any]] = {
        "decisions": {
            "min": 0,
            "max": 100,
            "default": 50,
            "weight": 1.0,
            "description": "Analysis depth and data requirements for decision-making"
        },
        "power": {
            "min": 0,
            "max": 100,
            "default": 50,
            "weight": 1.0,
            "description": "Autonomy boundaries and delegation comfort"
        },
        "fear": {
            "min": 0,
            "max": 100,
            "default": 50,
            "weight": 1.2,  # Higher weight for safety
            "description": "Risk tolerance and safety requirements"
        },
        "reward": {
            "min": 0,
            "max": 100,
            "default": 50,
            "weight": 0.8,
            "description": "Motivation patterns and achievement metrics"
        },
        "meaning": {
            "min": 0,
            "max": 100,
            "default": 50,
            "weight": 1.0,
            "description": "Value alignments and priority frameworks"
        }
    }
    
    # Negative Space Boundaries
    BOUNDARY_RISK_LEVELS: Dict[str, int] = {
        "critical": 100,
        "high": 75,
        "medium": 50,
        "low": 25,
        "minimal": 10
    }
    
    BOUNDARY_ENFORCEMENT_MODE: str = Field("strict", env="BOUNDARY_ENFORCEMENT_MODE")  # strict, flexible, learning
    
    # HILT (Human-in-the-Loop) Configuration
    HILT_CONFIDENCE_THRESHOLD: float = Field(0.7, env="HILT_CONFIDENCE_THRESHOLD")
    HILT_RISK_THRESHOLD: float = Field(0.8, env="HILT_RISK_THRESHOLD")
    HILT_AUTO_APPROVE_LOW_RISK: bool = Field(False, env="HILT_AUTO_APPROVE_LOW_RISK")
    HILT_APPROVAL_TIMEOUT: int = Field(300, env="HILT_APPROVAL_TIMEOUT")  # seconds
    
    # Agent Configuration
    AGENT_MAX_RETRIES: int = Field(3, env="AGENT_MAX_RETRIES")
    AGENT_TIMEOUT: int = Field(60, env="AGENT_TIMEOUT")
    AGENT_LEARNING_RATE: float = Field(0.1, env="AGENT_LEARNING_RATE")
    AGENT_EXPLORATION_RATE: float = Field(0.05, env="AGENT_EXPLORATION_RATE")
    
    # Security
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = Field(24, env="JWT_EXPIRATION_HOURS")
    CORS_ORIGINS: list = Field(["http://localhost:3000"], env="CORS_ORIGINS")
    
    # Monitoring & Logging
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    AUDIT_LOG_ENABLED: bool = Field(True, env="AUDIT_LOG_ENABLED")
    METRICS_ENABLED: bool = Field(True, env="METRICS_ENABLED")
    
    # Celery
    CELERY_BROKER_URL: str = Field("redis://localhost:6379", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field("redis://localhost:6379", env="CELERY_RESULT_BACKEND")
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list = ["json"]
    
    # Performance
    MAX_WORKERS: int = Field(10, env="MAX_WORKERS")
    BATCH_SIZE: int = Field(100, env="BATCH_SIZE")
    CACHE_TTL: int = Field(3600, env="CACHE_TTL")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @property
    def data_path(self) -> Path:
        """Get the data storage path"""
        path = Path("/data/bdt")
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def log_path(self) -> Path:
        """Get the log storage path"""
        path = Path("/logs/bdt")
        path.mkdir(parents=True, exist_ok=True)
        return path

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Export commonly used settings
settings = get_settings()