"""
BDT Phase 2: Vector Store Implementation
Manages document embeddings using Qdrant or ChromaDB
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import hashlib
import json
from datetime import datetime
import logging

# Support both Qdrant and ChromaDB
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct,
        Filter, FieldCondition, MatchValue,
        SearchRequest, SearchParams
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

import openai
from openai import AsyncOpenAI

from core.config import settings
from core.database import Document

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Vector search result"""
    document_id: str
    content: str
    metadata: Dict[str, Any]
    score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.document_id,
            'content': self.content[:500],
            'metadata': self.metadata,
            'relevance_score': self.score
        }


class VectorStore:
    """
    Unified vector store interface supporting Qdrant and ChromaDB
    Handles document embedding and similarity search
    """
    
    def __init__(self, backend: str = "auto"):
        """
        Initialize vector store
        
        Args:
            backend: 'qdrant', 'chromadb', or 'auto' (auto-detect)
        """
        self.backend = self._select_backend(backend)
        self.client = None
        self.openai = AsyncOpenAI(api_key=settings.openai_api_key)
        self.collection_name = f"{settings.qdrant_collection_prefix}_phase2"
        
        logger.info(f"Vector store initialized with backend: {self.backend}")
    
    def _select_backend(self, backend: str) -> str:
        """Select the vector store backend"""
        if backend == "auto":
            if QDRANT_AVAILABLE:
                return "qdrant"
            elif CHROMADB_AVAILABLE:
                return "chromadb"
            else:
                raise ImportError("No vector store backend available. Install qdrant-client or chromadb")
        
        if backend == "qdrant" and not QDRANT_AVAILABLE:
            raise ImportError("Qdrant requested but not installed")
        
        if backend == "chromadb" and not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB requested but not installed")
        
        return backend
    
    async def initialize(self):
        """Initialize the vector store connection and collections"""
        if self.backend == "qdrant":
            await self._init_qdrant()
        elif self.backend == "chromadb":
            await self._init_chromadb()
    
    async def _init_qdrant(self):
        """Initialize Qdrant connection"""
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
            timeout=30
        )
        
        # Create collection if it doesn't exist
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created Qdrant collection: {self.collection_name}")
        else:
            logger.info(f"Using existing Qdrant collection: {self.collection_name}")
    
    async def _init_chromadb(self):
        """Initialize ChromaDB connection"""
        self.client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=None  # We'll handle embeddings ourselves
            )
            logger.info(f"Using existing ChromaDB collection: {self.collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
                embedding_function=None
            )
            logger.info(f"Created ChromaDB collection: {self.collection_name}")
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embeddings for text using OpenAI
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            response = await self.openai.embeddings.create(
                model=settings.openai_embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        try:
            # OpenAI supports batch embedding
            response = await self.openai.embeddings.create(
                model=settings.openai_embedding_model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            # Fallback to individual embedding
            embeddings = []
            for text in texts:
                embedding = await self.embed_text(text)
                embeddings.append(embedding)
            return embeddings
    
    async def index_document(
        self,
        document: Document,
        force: bool = False
    ) -> bool:
        """
        Index a single document
        
        Args:
            document: Document to index
            force: Force re-indexing even if already exists
            
        Returns:
            Success status
        """
        try:
            # Check if already indexed
            if not force and document.embedding_id:
                return True
            
            # Generate embedding
            embedding = await self.embed_text(document.content)
            
            # Prepare metadata
            metadata = document.metadata.copy() if document.metadata else {}
            metadata.update({
                'doc_id': document.id,
                'doc_type': document.doc_type,
                'source': document.source,
                'timestamp': document.source_timestamp.isoformat() if document.source_timestamp else None
            })
            
            # Store in vector database
            if self.backend == "qdrant":
                await self._index_qdrant(document.id, embedding, metadata)
            else:
                await self._index_chromadb(document.id, document.content, embedding, metadata)
            
            logger.debug(f"Indexed document: {document.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing document {document.id}: {e}")
            return False
    
    async def _index_qdrant(self, doc_id: str, embedding: List[float], metadata: Dict[str, Any]):
        """Index document in Qdrant"""
        point = PointStruct(
            id=hashlib.md5(doc_id.encode()).hexdigest()[:16],
            vector=embedding,
            payload=metadata
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
    
    async def _index_chromadb(
        self,
        doc_id: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ):
        """Index document in ChromaDB"""
        self.collection.upsert(
            ids=[doc_id],
            documents=[content],
            embeddings=[embedding],
            metadatas=[metadata]
        )
    
    async def index_batch(
        self,
        documents: List[Document],
        batch_size: int = 100,
        progress_callback: Optional[callable] = None
    ) -> int:
        """
        Index multiple documents in batches
        
        Args:
            documents: List of documents to index
            batch_size: Number of documents per batch
            progress_callback: Callback for progress updates
            
        Returns:
            Number of documents successfully indexed
        """
        indexed = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            
            # Generate embeddings for batch
            texts = [doc.content for doc in batch]
            embeddings = await self.embed_batch(texts)
            
            # Index each document
            for doc, embedding in zip(batch, embeddings):
                metadata = doc.metadata.copy() if doc.metadata else {}
                metadata.update({
                    'doc_id': doc.id,
                    'doc_type': doc.doc_type,
                    'source': doc.source,
                    'timestamp': doc.source_timestamp.isoformat() if doc.source_timestamp else None
                })
                
                if self.backend == "qdrant":
                    await self._index_qdrant(doc.id, embedding, metadata)
                else:
                    await self._index_chromadb(doc.id, doc.content, embedding, metadata)
                
                indexed += 1
            
            # Report progress
            if progress_callback:
                progress_callback(indexed, len(documents))
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)
        
        logger.info(f"Indexed {indexed} documents")
        return indexed
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        persona_id: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search for similar documents
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Metadata filters
            persona_id: Filter by persona
            
        Returns:
            List of search results
        """
        # Generate query embedding
        query_embedding = await self.embed_text(query)
        
        # Perform search
        if self.backend == "qdrant":
            return await self._search_qdrant(query_embedding, top_k, filters, persona_id)
        else:
            return await self._search_chromadb(query_embedding, query, top_k, filters, persona_id)
    
    async def _search_qdrant(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]],
        persona_id: Optional[str]
    ) -> List[SearchResult]:
        """Search in Qdrant"""
        # Build filter
        filter_conditions = []
        
        if filters:
            for key, value in filters.items():
                filter_conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
        
        if persona_id:
            filter_conditions.append(
                FieldCondition(key="persona_id", match=MatchValue(value=persona_id))
            )
        
        search_filter = Filter(must=filter_conditions) if filter_conditions else None
        
        # Perform search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=search_filter
        )
        
        # Convert to SearchResult
        search_results = []
        for result in results:
            search_results.append(SearchResult(
                document_id=result.payload.get('doc_id', ''),
                content=result.payload.get('content', ''),
                metadata=result.payload,
                score=result.score
            ))
        
        return search_results
    
    async def _search_chromadb(
        self,
        query_embedding: List[float],
        query_text: str,
        top_k: int,
        filters: Optional[Dict[str, Any]],
        persona_id: Optional[str]
    ) -> List[SearchResult]:
        """Search in ChromaDB"""
        # Build where clause
        where_clause = {}
        
        if filters:
            where_clause.update(filters)
        
        if persona_id:
            where_clause['persona_id'] = persona_id
        
        # Perform search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause if where_clause else None
        )
        
        # Convert to SearchResult
        search_results = []
        
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                search_results.append(SearchResult(
                    document_id=doc_id,
                    content=results['documents'][0][i] if results['documents'] else '',
                    metadata=results['metadatas'][0][i] if results['metadatas'] else {},
                    score=1 - results['distances'][0][i] if results['distances'] else 0.0
                ))
        
        return search_results
    
    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        keyword_weight: float = 0.3,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Hybrid search combining vector similarity and keyword matching
        
        Args:
            query: Search query
            top_k: Number of results
            keyword_weight: Weight for keyword matching (0-1)
            filters: Metadata filters
            
        Returns:
            List of search results
        """
        # Get vector search results
        vector_results = await self.search(query, top_k * 2, filters)
        
        # Score keyword matches
        query_terms = query.lower().split()
        
        for result in vector_results:
            content_lower = result.content.lower()
            
            # Calculate keyword score
            keyword_score = 0
            for term in query_terms:
                if term in content_lower:
                    # Weight by term frequency
                    keyword_score += content_lower.count(term) / len(content_lower.split())
            
            # Normalize keyword score
            keyword_score = min(keyword_score / len(query_terms), 1.0) if query_terms else 0
            
            # Combine scores
            result.score = (1 - keyword_weight) * result.score + keyword_weight * keyword_score
        
        # Re-sort by combined score
        vector_results.sort(key=lambda x: x.score, reverse=True)
        
        return vector_results[:top_k]
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the vector store
        
        Args:
            document_id: Document ID to delete
            
        Returns:
            Success status
        """
        try:
            if self.backend == "qdrant":
                point_id = hashlib.md5(document_id.encode()).hexdigest()[:16]
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=[point_id]
                )
            else:
                self.collection.delete(ids=[document_id])
            
            logger.debug(f"Deleted document from vector store: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False
    
    async def update_metadata(
        self,
        document_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update document metadata
        
        Args:
            document_id: Document ID
            metadata: New metadata
            
        Returns:
            Success status
        """
        try:
            if self.backend == "qdrant":
                point_id = hashlib.md5(document_id.encode()).hexdigest()[:16]
                self.client.set_payload(
                    collection_name=self.collection_name,
                    payload=metadata,
                    points=[point_id]
                )
            else:
                # ChromaDB requires re-upserting
                # Fetch existing document first
                result = self.collection.get(ids=[document_id])
                if result['ids']:
                    self.collection.update(
                        ids=[document_id],
                        metadatas=[metadata]
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating metadata for {document_id}: {e}")
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        stats = {
            'backend': self.backend,
            'collection': self.collection_name
        }
        
        if self.backend == "qdrant":
            info = self.client.get_collection(self.collection_name)
            stats['document_count'] = info.vectors_count
            stats['dimension'] = info.config.params.vectors.size
        else:
            # ChromaDB statistics
            stats['document_count'] = self.collection.count()
            
        return stats
    
    async def close(self):
        """Close vector store connection"""
        # Qdrant and ChromaDB clients don't require explicit closing
        pass


# Simplified vector store for demos
class SimpleVectorStore:
    """
    Simple in-memory vector store for prototyping
    No external dependencies required
    """
    
    def __init__(self):
        self.documents = {}
        self.embeddings = {}
        self.openai = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any] = None):
        """Add document to store"""
        # Generate embedding
        response = await self.openai.embeddings.create(
            model=settings.openai_embedding_model,
            input=content
        )
        embedding = response.data[0].embedding
        
        # Store
        self.documents[doc_id] = {
            'content': content,
            'metadata': metadata or {},
            'embedding': embedding
        }
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        # Generate query embedding
        response = await self.openai.embeddings.create(
            model=settings.openai_embedding_model,
            input=query
        )
        query_embedding = np.array(response.data[0].embedding)
        
        # Calculate similarities
        scores = []
        for doc_id, doc_data in self.documents.items():
            doc_embedding = np.array(doc_data['embedding'])
            
            # Cosine similarity
            similarity = np.dot(query_embedding, doc_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
            )
            
            scores.append((doc_id, similarity, doc_data))
        
        # Sort by similarity
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top results
        results = []
        for doc_id, score, doc_data in scores[:top_k]:
            results.append({
                'id': doc_id,
                'content': doc_data['content'],
                'metadata': doc_data['metadata'],
                'score': float(score)
            })
        
        return results


# Export main classes
__all__ = [
    'VectorStore',
    'SimpleVectorStore',
    'SearchResult'
]
