import psycopg2
import os
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

def init_database():
    """Initialize all database tables"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Create tables
    queries = [
        """CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )""",
        
        """CREATE TABLE IF NOT EXISTS twins (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id),
            name VARCHAR(255),
            twin_type VARCHAR(50),
            capability_level INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT NOW()
        )""",
        
        """CREATE TABLE IF NOT EXISTS data_sources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            twin_id UUID REFERENCES twins(id),
            source_type VARCHAR(50),
            content TEXT,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )""",
        
        """CREATE TABLE IF NOT EXISTS embeddings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            twin_id UUID REFERENCES twins(id),
            content TEXT,
            embedding VECTOR(1536),
            source_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        )""",
        
        """CREATE TABLE IF NOT EXISTS chat_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            twin_id UUID REFERENCES twins(id),
            user_message TEXT,
            assistant_message TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )"""
    ]
    
    for query in queries:
        try:
            cur.execute(query)
            print(f" Table created/verified")
        except Exception as e:
            print(f"Table creation note: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    print(" Database initialized")

if __name__ == "__main__":
    init_database()
