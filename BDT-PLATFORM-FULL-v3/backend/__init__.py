"""
BDT Platform Backend Package
Version 2.0.0
"""

__version__ = "2.0.0"
__author__ = "BDT Platform Team"

# Import key components for easier access
from .main import app, get_db
from .graph_service import graph_service
from .cache_service import cache
from .dashboard_service import dashboard_service
from .tasks import celery_app

__all__ = [
    "app",
    "get_db",
    "graph_service",
    "cache",
    "dashboard_service",
    "celery_app"
]
