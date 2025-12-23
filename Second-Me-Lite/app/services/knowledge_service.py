"""
service about knowledge retrieve (L0 only)
L1 knowledge retrieval has been moved to app.services.L1
"""
import logging
from typing import List, Tuple, Optional
from app.services.embedding_service import EmbeddingService, ChunkDTO

logger = logging.getLogger(__name__)


class L0KnowledgeRetriever:
    """L0 knowledge retriever"""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        similarity_threshold: float = 0.5,
        max_chunks: int = 3,
    ):
        """
        init L0 knowledge retriever

        Args:
            embedding_service: Embedding service instance
            similarity_threshold: only return contents whose similarity bigger than this value
            max_chunks: the maximum number of return chunks
        """
        self.embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold
        self.max_chunks = max_chunks

    def retrieve(self, query: str) -> str:
        """
        retrieve L0 knowledge

        Args:
            query: query content

        Returns:
            str: structured knowledge content, or empty string if no relevant knowledge found
        """
        try:
            # search related chunks
            similar_chunks: List[
                Tuple[ChunkDTO, float]
            ] = self.embedding_service.search_similar_chunks(
                query=query, limit=self.max_chunks
            )

            # filter out low similarity chunks
            if not similar_chunks:
                return ""

            knowledge_parts = []
            for chunk, similarity in similar_chunks:
                if similarity >= self.similarity_threshold:
                    knowledge_parts.append(chunk.content)

            if not knowledge_parts:
                return ""

            # merge multiple knowledge parts into one
            return "\n\n".join(knowledge_parts)

        except Exception as e:
            logger.error(f"L0 knowledge retrieval failed: {str(e)}")
            return ""


# create default L0 retriever instance
default_retriever = L0KnowledgeRetriever(
    embedding_service=EmbeddingService(), similarity_threshold=0.5, max_chunks=3
)
