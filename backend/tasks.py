"""
Background Task Processing with Celery
Handles async operations for data sync and document processing
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json
import asyncio
from functools import wraps

from celery import Celery, Task
from celery.schedules import crontab
from kombu import Queue, Exchange
import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import services
from .graph_service import graph_service
from .cache_service import cache

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_CLIENT = redis.from_url(REDIS_URL)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL",
    "postgresql://bdtadmin:PumpkinPi14$@bdt-platform-db.postgres.database.azure.com:5432/bdtplatform?sslmode=require")

# Alternative username handling
if "bdtadmin" in DATABASE_URL and not os.getenv("DATABASE_URL"):
    # Try alternative username if default fails
    ALT_DATABASE_URL = DATABASE_URL.replace("bdtadmin", "btadmin")
else:
    ALT_DATABASE_URL = DATABASE_URL

# Celery configuration
celery_app = Celery(
    'bdt_tasks',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['backend.tasks']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes soft limit
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    
    # Queue configuration
    task_default_queue='default',
    task_queues=(
        Queue('default', Exchange('default'), routing_key='default'),
        Queue('sync', Exchange('sync'), routing_key='sync'),
        Queue('documents', Exchange('documents'), routing_key='documents'),
        Queue('analytics', Exchange('analytics'), routing_key='analytics'),
    ),
    
    # Route tasks to specific queues
    task_routes={
        'tasks.sync_user_data': {'queue': 'sync'},
        'tasks.process_document': {'queue': 'documents'},
        'tasks.generate_analytics': {'queue': 'analytics'},
    },
    
    # Retry configuration
    task_default_retry_delay=60,  # 60 seconds
    task_max_retries=3,
    
    # Result backend configuration
    result_expires=3600,  # Results expire after 1 hour
    result_compression='gzip',
)

# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    'sync-all-users-daily': {
        'task': 'tasks.sync_all_users',
        'schedule': crontab(hour=2, minute=0),  # Run at 2 AM daily
    },
    'cleanup-old-tasks': {
        'task': 'tasks.cleanup_old_tasks',
        'schedule': crontab(hour=3, minute=0),  # Run at 3 AM daily
    },
    'generate-daily-analytics': {
        'task': 'tasks.generate_daily_analytics',
        'schedule': crontab(hour=6, minute=0),  # Run at 6 AM daily
    },
}

class CallbackTask(Task):
    """Task with callbacks for success/failure"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Success callback"""
        logger.info(f"Task {task_id} succeeded with result: {retval}")
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Failure callback"""
        logger.error(f"Task {task_id} failed with exception: {exc}")

def async_to_sync(async_func):
    """Convert async function to sync for Celery"""
    @wraps(async_func)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

# =====================
# SYNC TASKS
# =====================

@celery_app.task(bind=True, base=CallbackTask, name='tasks.sync_user_data')
def sync_user_data(self, user_id: str, access_token: str, sources: list = None) -> Dict:
    """
    Sync all Microsoft 365 data for a user
    """
    try:
        # Update task status
        self.update_state(state='PROGRESS', meta={'status': 'Starting sync...'})
        
        # Get database session
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Import here to avoid circular imports
        from .main import store_with_source_metadata, Twin, User
        
        # Get user and twin
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        twin = db.query(Twin).filter(Twin.user_id == user_id).first()
        if not twin:
            # Create twin if doesn't exist
            twin = Twin(
                user_id=user_id,
                name=f"{user.name}'s Digital Twin",
                twin_type="individual",
                capability_level="L2"
            )
            db.add(twin)
            db.commit()
        
        twin_id = str(twin.id)
        
        # Define callback for storing data
        @async_to_sync
        async def store_callback(twin_id: str, text: str, source_type: str, metadata: Dict):
            """Store data in ChromaDB and PostgreSQL"""
            try:
                store_with_source_metadata(
                    twin_id=twin_id,
                    text=text,
                    source_type=source_type,
                    metadata=metadata,
                    db=db
                )
            except Exception as e:
                logger.error(f"Failed to store {source_type} data: {e}")
        
        # Default to all sources
        if not sources:
            sources = ["emails", "calendar", "files", "teams"]
        
        results = {}
        total_synced = 0
        
        # Sync each source
        for source in sources:
            try:
                self.update_state(
                    state='PROGRESS',
                    meta={'status': f'Syncing {source}...', 'progress': 0}
                )
                
                if source == "emails":
                    result = async_to_sync(graph_service.sync_emails)(
                        access_token, twin_id, callback=store_callback
                    )
                elif source == "calendar":
                    result = async_to_sync(graph_service.sync_calendar)(
                        access_token, twin_id, callback=store_callback
                    )
                elif source == "files":
                    result = async_to_sync(graph_service.sync_files)(
                        access_token, twin_id, callback=store_callback
                    )
                elif source == "teams":
                    result = async_to_sync(graph_service.sync_teams_messages)(
                        access_token, twin_id, callback=store_callback
                    )
                else:
                    continue
                
                results[source] = result
                total_synced += result.get("synced_count", 0)
                
                # Update progress
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'status': f'Completed {source}',
                        'synced': total_synced,
                        'current_source': source
                    }
                )
                
            except Exception as e:
                logger.error(f"Failed to sync {source}: {e}")
                results[source] = {"success": False, "error": str(e)}
        
        # Store sync status in Redis
        sync_key = f"sync:user:{user_id}:last"
        REDIS_CLIENT.setex(
            sync_key,
            86400,  # Expire after 24 hours
            json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "total_synced": total_synced,
                "results": results
            })
        )
        
        # Close database session
        db.close()
        
        return {
            "success": True,
            "user_id": user_id,
            "total_synced": total_synced,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Sync task failed for user {user_id}: {e}")
        self.retry(exc=e, countdown=60)
        return {
            "success": False,
            "error": str(e)
        }

@celery_app.task(bind=True, name='tasks.process_document')
def process_document(
    self,
    file_path: str,
    twin_id: str,
    file_type: str,
    user_id: str
) -> Dict:
    """
    Process uploaded document asynchronously
    """
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Processing document...'})
        
        # Get database session
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Import processing functions
        from .main import store_with_source_metadata
        
        # Process based on file type
        text_content = ""
        metadata = {
            "file_name": os.path.basename(file_path),
            "file_type": file_type,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        if file_type == "pdf":
            import PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages):
                    text_content += f"\n--- Page {page_num + 1} ---\n"
                    text_content += page.extract_text()
                    
                    # Store each page separately for better retrieval
                    if len(text_content) > 1000:
                        store_with_source_metadata(
                            twin_id=twin_id,
                            text=text_content,
                            source_type="upload",
                            metadata={**metadata, "page": page_num + 1},
                            db=db
                        )
                        text_content = ""
        
        elif file_type == "docx":
            from docx import Document
            doc = Document(file_path)
            for para in doc.paragraphs:
                text_content += para.text + "\n"
                
                # Store in chunks
                if len(text_content) > 1000:
                    store_with_source_metadata(
                        twin_id=twin_id,
                        text=text_content,
                        source_type="upload",
                        metadata=metadata,
                        db=db
                    )
                    text_content = ""
        
        elif file_type in ["txt", "md"]:
            with open(file_path, 'r', encoding='utf-8') as file:
                text_content = file.read()
                
                # Split into chunks
                chunk_size = 1000
                for i in range(0, len(text_content), chunk_size):
                    chunk = text_content[i:i+chunk_size]
                    store_with_source_metadata(
                        twin_id=twin_id,
                        text=chunk,
                        source_type="upload",
                        metadata={**metadata, "chunk": i // chunk_size},
                        db=db
                    )
        
        else:
            # Unsupported file type
            raise ValueError(f"Unsupported file type: {file_type}")
        
        # Store any remaining content
        if text_content:
            store_with_source_metadata(
                twin_id=twin_id,
                text=text_content,
                source_type="upload",
                metadata=metadata,
                db=db
            )
        
        # Clean up file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Update cache
        cache_key = f"user:{user_id}:documents"
        cache.delete(cache_key)
        
        db.close()
        
        return {
            "success": True,
            "file": os.path.basename(file_path),
            "status": "processed"
        }
        
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        self.retry(exc=e, countdown=30)
        return {
            "success": False,
            "error": str(e)
        }

@celery_app.task(name='tasks.generate_analytics')
def generate_analytics(user_id: str, twin_id: str) -> Dict:
    """
    Generate analytics for dashboard views
    """
    try:
        # Get database session
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        from .main import EmbeddingRecord, Twin
        
        # Get twin
        twin = db.query(Twin).filter(Twin.id == twin_id).first()
        if not twin:
            raise ValueError(f"Twin {twin_id} not found")
        
        # Generate analytics
        analytics = {
            "summary": {},
            "by_source": {},
            "trends": [],
            "insights": []
        }
        
        # Count by source type
        source_counts = {}
        records = db.query(EmbeddingRecord).filter(
            EmbeddingRecord.twin_id == twin_id
        ).all()
        
        for record in records:
            source = record.source_type
            if source not in source_counts:
                source_counts[source] = 0
            source_counts[source] += 1
        
        analytics["by_source"] = source_counts
        analytics["summary"]["total_records"] = len(records)
        analytics["summary"]["sources"] = len(source_counts)
        
        # Generate time-based trends
        from collections import defaultdict
        daily_counts = defaultdict(int)
        
        for record in records:
            day = record.created_at.date()
            daily_counts[str(day)] += 1
        
        analytics["trends"] = [
            {"date": date, "count": count}
            for date, count in sorted(daily_counts.items())[-30:]  # Last 30 days
        ]
        
        # Generate insights
        if source_counts.get("email", 0) > 100:
            analytics["insights"].append("High email volume detected")
        
        if source_counts.get("calendar", 0) > 50:
            analytics["insights"].append("Busy calendar schedule")
        
        if source_counts.get("files", 0) > 200:
            analytics["insights"].append("Large document library")
        
        # Cache results
        cache_key = f"analytics:{twin_id}"
        cache.set(cache_key, json.dumps(analytics), expire=3600)
        
        db.close()
        
        return {
            "success": True,
            "analytics": analytics
        }
        
    except Exception as e:
        logger.error(f"Analytics generation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@celery_app.task(name='tasks.sync_all_users')
def sync_all_users() -> Dict:
    """
    Periodic task to sync all active users
    """
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        from .main import User
        
        # Get all users with valid tokens
        users = db.query(User).filter(
            User.metadata.op("->")("access_token") != None
        ).all()
        
        synced = 0
        failed = 0
        
        for user in users:
            try:
                # Check if token is expired
                token_data = user.metadata.get("access_token", {})
                if not token_data:
                    continue
                
                # Queue sync task
                sync_user_data.delay(
                    str(user.id),
                    token_data.get("access_token")
                )
                synced += 1
                
            except Exception as e:
                logger.error(f"Failed to queue sync for user {user.id}: {e}")
                failed += 1
        
        db.close()
        
        return {
            "success": True,
            "users_synced": synced,
            "failed": failed
        }
        
    except Exception as e:
        logger.error(f"Sync all users failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@celery_app.task(name='tasks.cleanup_old_tasks')
def cleanup_old_tasks() -> Dict:
    """
    Clean up old task results and temporary files
    """
    try:
        # Clean up old task results from Redis
        pattern = "celery-task-meta-*"
        cursor = 0
        deleted = 0
        
        while True:
            cursor, keys = REDIS_CLIENT.scan(cursor, match=pattern, count=100)
            
            for key in keys:
                # Check if older than 24 hours
                ttl = REDIS_CLIENT.ttl(key)
                if ttl < 0 or ttl > 86400:
                    REDIS_CLIENT.delete(key)
                    deleted += 1
            
            if cursor == 0:
                break
        
        # Clean up temporary files
        temp_dir = "/tmp/bdt_uploads"
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                # Delete files older than 24 hours
                if os.path.getctime(file_path) < time.time() - 86400:
                    os.remove(file_path)
        
        return {
            "success": True,
            "deleted_tasks": deleted
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@celery_app.task(name='tasks.generate_daily_analytics')
def generate_daily_analytics() -> Dict:
    """
    Generate daily analytics for all users
    """
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        from .main import User, Twin
        
        # Get all users
        users = db.query(User).all()
        
        generated = 0
        
        for user in users:
            try:
                # Get user's twin
                twin = db.query(Twin).filter(Twin.user_id == user.id).first()
                if twin:
                    generate_analytics.delay(str(user.id), str(twin.id))
                    generated += 1
                    
            except Exception as e:
                logger.error(f"Failed to generate analytics for user {user.id}: {e}")
        
        db.close()
        
        return {
            "success": True,
            "analytics_generated": generated
        }
        
    except Exception as e:
        logger.error(f"Daily analytics generation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# Task status helper functions
def get_task_status(task_id: str) -> Dict:
    """Get status of a Celery task"""
    try:
        from celery.result import AsyncResult
        result = AsyncResult(task_id, app=celery_app)
        
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.ready() else None,
            "info": result.info
        }
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "ERROR",
            "error": str(e)
        }

def cancel_task(task_id: str) -> bool:
    """Cancel a running task"""
    try:
        from celery.result import AsyncResult
        result = AsyncResult(task_id, app=celery_app)
        result.revoke(terminate=True)
        return True
    except:
        return False
