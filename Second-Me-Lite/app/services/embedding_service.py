"""
Embedding service for handling embeddings and similarity search
"""
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from app.core.vector import get_embedding as _get_embedding, search_similar_chunks as _search_similar_chunks
from app.core.database import SessionLocal
import numpy as np
import logging

logger = logging.getLogger(__name__)


class ChunkDTO:
    """Data Transfer Object for Chunk"""
    def __init__(self, id: int, content: str, document_id: Optional[int] = None, 
                 tags: Optional[str] = None, topic: Optional[str] = None):
        self.id = id
        self.content = content
        self.document_id = document_id
        self.tags = tags
        self.topic = topic


class EmbeddingService:
    """Service for handling embeddings and similarity search"""
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize EmbeddingService
        
        Args:
            db: Optional database session. If not provided, a new session will be created when needed.
        """
        self._db = db
    
    def _get_db(self) -> Session:
        """Get database session"""
        if self._db:
            return self._db
        return SessionLocal()
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding vector for text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if failed
        """
        try:
            return _get_embedding(text)
        except Exception as e:
            logger.error(f"Failed to get embedding: {str(e)}")
            return None
    
    def search_similar_chunks(self, query: str, limit: int = 3) -> List[Tuple[ChunkDTO, float]]:
        """
        Search for similar chunks
        
        Args:
            query: Query text
            limit: Maximum number of results
            
        Returns:
            List of tuples (ChunkDTO, similarity_score)
        """
        db = self._get_db()
        try:
            # Get query embedding
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                logger.error("Failed to get embedding for query")
                return []
            
            # Search similar chunks
            results = _search_similar_chunks(db, query_embedding, limit)
            
            # Convert to ChunkDTO tuples
            chunks = []
            for result in results:
                chunk_dto = ChunkDTO(
                    id=result['id'],
                    content=result['content'],
                    document_id=result.get('document_id'),
                    tags=result.get('tags'),
                    topic=result.get('topic')
                )
                chunks.append((chunk_dto, result['similarity']))
            
            return chunks
        except Exception as e:
            logger.error(f"Failed to search similar chunks: {str(e)}")
            return []
        finally:
            # Only close if we created the session
            if not self._db:
                db.close()
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {str(e)}")
            return 0.0

