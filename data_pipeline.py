"""
Complete Data Pipeline with SQL, Vector, and Graph databases
"""
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
import asyncio

# Database imports
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np

# Vector database
import chromadb
from chromadb.config import Settings

# For embeddings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class DataPipeline:
    """Complete pipeline for Tyler's data"""
    
    def __init__(self):
        # PostgreSQL connection
        self.db_url = os.getenv("DATABASE_URL", 
            "postgresql://bdtadmin:PumpkinPi14$@bdt-platform-db.postgres.database.azure.com:5432/bdtplatform?sslmode=require")
        
        # Initialize ChromaDB for vector storage
        self.chroma_client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory="/tmp/chroma"
        ))
        
        # Create/get collection for Tyler
        self.tyler_collection = self.chroma_client.get_or_create_collection(
            name="tyler_helwig_data"
        )
        
        # Initialize embedding model
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize database tables
        self.init_database()
    
    def init_database(self):
        """Create tables in PostgreSQL"""
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            
            # Tyler's data table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tyler_data (
                    id SERIAL PRIMARY KEY,
                    data_type VARCHAR(50),
                    subject VARCHAR(500),
                    content TEXT,
                    metadata JSONB,
                    embedding_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Relationships table (for graph)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tyler_relationships (
                    id SERIAL PRIMARY KEY,
                    source_id INTEGER REFERENCES tyler_data(id),
                    target_id INTEGER REFERENCES tyler_data(id),
                    relationship_type VARCHAR(100),
                    strength FLOAT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            conn.commit()
            cur.close()
            conn.close()
            logger.info(" Database tables initialized")
        except Exception as e:
            logger.error(f"Database init error: {e}")
    
    async def process_and_store(self, data_type: str, items: List[Dict]) -> int:
        """Process data through full pipeline"""
        stored_count = 0
        
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            
            for item in items:
                # 1. Store in PostgreSQL
                cur.execute("""
                    INSERT INTO tyler_data (data_type, subject, content, metadata)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (
                    data_type,
                    item.get("subject", item.get("name", "")),
                    item.get("preview", item.get("content", "")),
                    json.dumps(item)
                ))
                
                record_id = cur.fetchone()[0]
                
                # 2. Create embedding and store in ChromaDB
                text_to_embed = f"{item.get('subject', '')} {item.get('preview', '')}"
                embedding = self.embedder.encode(text_to_embed).tolist()
                
                self.tyler_collection.add(
                    embeddings=[embedding],
                    documents=[text_to_embed],
                    metadatas=[{"type": data_type, "sql_id": record_id}],
                    ids=[f"{data_type}_{record_id}"]
                )
                
                # 3. Update SQL with embedding reference
                cur.execute("""
                    UPDATE tyler_data 
                    SET embedding_id = %s 
                    WHERE id = %s
                """, (f"{data_type}_{record_id}", record_id))
                
                stored_count += 1
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f" Stored {stored_count} {data_type} items in all databases")
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
        
        return stored_count
    
    async def semantic_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search using vector similarity"""
        # Create query embedding
        query_embedding = self.embedder.encode(query).tolist()
        
        # Search in ChromaDB
        results = self.tyler_collection.query(
            query_embeddings=[query_embedding],
            n_results=limit
        )
        
        # Get full records from PostgreSQL
        full_results = []
        if results['ids'][0]:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            for idx, doc_id in enumerate(results['ids'][0]):
                sql_id = results['metadatas'][0][idx]['sql_id']
                cur.execute("""
                    SELECT * FROM tyler_data WHERE id = %s
                """, (sql_id,))
                
                record = cur.fetchone()
                if record:
                    record['relevance_score'] = results['distances'][0][idx]
                    full_results.append(dict(record))
            
            cur.close()
            conn.close()
        
        return full_results
    
    def build_knowledge_graph(self):
        """Build relationships between Tyler's data"""
        # This would analyze data and create graph relationships
        # For now, a simplified version
        logger.info("Building knowledge graph...")
        # Implementation would go here
        pass

# Global pipeline instance
data_pipeline = DataPipeline()
