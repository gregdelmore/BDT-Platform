"""
Database setup - Create tables BEFORE pulling any data
"""
import psycopg2
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        # Your Azure PostgreSQL connection
        self.connection_string = "postgresql://bdtadmin:PumpkinPi14$@bdt-platform-db.postgres.database.azure.com:5432/bdtplatform?sslmode=require"
        self.connected = False
        self.test_connection()
    
    def test_connection(self):
        """Test if we can connect to database"""
        try:
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor()
            cur.execute("SELECT version()")
            version = cur.fetchone()
            logger.info(f" Database connected: {version[0][:30]}...")
            cur.close()
            conn.close()
            self.connected = True
            return True
        except Exception as e:
            logger.error(f" Database connection failed: {e}")
            self.connected = False
            return False
    
    def create_tables(self):
        """Create tables for Tyler's data"""
        if not self.connected:
            return False
        
        try:
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor()
            
            # Main data table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tyler_data (
                    id SERIAL PRIMARY KEY,
                    data_type VARCHAR(50),
                    subject VARCHAR(500),
                    sender VARCHAR(255),
                    content TEXT,
                    preview TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    indexed_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create indexes for searching
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_tyler_type 
                ON tyler_data(data_type)
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_tyler_subject 
                ON tyler_data(subject)
            """)
            
            conn.commit()
            cur.close()
            conn.close()
            logger.info(" Tables created successfully")
            return True
        except Exception as e:
            logger.error(f" Table creation failed: {e}")
            return False
    
    def check_storage_ready(self):
        """Verify storage is ready for data"""
        if not self.connected:
            return {"ready": False, "error": "Not connected"}
        
        try:
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor()
            
            # Check if table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'tyler_data'
                )
            """)
            table_exists = cur.fetchone()[0]
            
            # Count existing records
            if table_exists:
                cur.execute("SELECT COUNT(*) FROM tyler_data")
                count = cur.fetchone()[0]
            else:
                count = 0
            
            cur.close()
            conn.close()
            
            return {
                "ready": table_exists,
                "existing_records": count,
                "database": "PostgreSQL on Azure",
                "status": "Ready for data" if table_exists else "Tables not created"
            }
        except Exception as e:
            return {"ready": False, "error": str(e)}

db_manager = DatabaseManager()
