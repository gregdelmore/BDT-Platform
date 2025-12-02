"""
FastAPI main application for BDT Phase 4
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Dict, Any

from ..config import settings
from ..database import init_db
from .routes import ontology, agent, hilt, monitoring
from .websocket import websocket_endpoint
from .middleware.auth import AuthMiddleware
from .middleware.audit import AuditMiddleware

logger = logging.getLogger(__name__)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting BDT Phase 4 API")
    init_db()
    
    yield
    
    # Shutdown
    logger.info("Shutting down BDT Phase 4 API")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Behavioral Digital Twin Phase 4 - L4 Delegated Agent API",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(AuthMiddleware)
app.add_middleware(AuditMiddleware)

# Include routers
app.include_router(
    ontology.router,
    prefix="/api/v1/ontology",
    tags=["Fourth Ontology"]
)

app.include_router(
    agent.router,
    prefix="/api/v1/agent",
    tags=["L4 Agent"]
)

app.include_router(
    hilt.router,
    prefix="/api/v1/hilt",
    tags=["HILT Control"]
)

app.include_router(
    monitoring.router,
    prefix="/api/v1/monitoring",
    tags=["Monitoring"]
)

# WebSocket endpoint
app.add_api_websocket_route("/ws", websocket_endpoint)

# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "BDT Phase 4 - L4 Delegated Agent API",
        "documentation": "/docs",
        "health": "/health"
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)