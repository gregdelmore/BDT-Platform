"""
PRODUCTION Database Manager - Proper connection handling
"""
import os
import psycopg2
from psycopg2 import pool
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Production-grade database manager with connection pooling"""
    
    def __init__(self):
        # Get from environment variable (PROPER way)
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://bdtadmin:PumpkinPi14$@bdt-platform-db.postgres.database.azure.com:5432/bdtplatform?sslmode=require"
        )
        
        # Create connection pool (PROPER for production)
        self.connection_pool = None
        self.initialize_pool()
    
    def initialize_pool(self):
        """Create connection pool for production use"""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1,  # Min connections
                20, # Max connections
                self.database_url
            )
            if self.connection_pool:
                logger.info(" Database connection pool created")
                self.create_tables()
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            self.connection_pool = None
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool with proper cleanup"""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def create_tables(self):
        """Create production tables with proper schema"""
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                
                # Tyler's data table with proper indexes
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tyler_data (
                        id SERIAL PRIMARY KEY,
                        data_type VARCHAR(50) NOT NULL,
                        subject VARCHAR(500),
                        sender VARCHAR(255),
                        content TEXT,
                        preview TEXT,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for performance
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tyler_data_type 
                    ON tyler_data(data_type)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tyler_subject_gin 
                    ON tyler_data USING gin(to_tsvector('english', subject))
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tyler_content_gin 
                    ON tyler_data USING gin(to_tsvector('english', content))
                """)
                
                logger.info(" Production tables created with indexes")
                
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
    
    def is_connected(self):
        """Check if database is accessible"""
        if not self.connection_pool:
            return False
        
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                return True
        except:
            return False

# Singleton instance
db_manager = DatabaseManager()
