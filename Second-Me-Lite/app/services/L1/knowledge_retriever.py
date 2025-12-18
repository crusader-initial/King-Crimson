"""
L1 knowledge retriever service
"""
import logging
import json
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from app.services.embedding_service import EmbeddingService
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


class GlobalBio:
    """Global Bio 数据类，包含 shades 信息"""
    def __init__(self, shades: List[Dict[str, Any]] = None):
        self.shades = shades or []


def get_latest_global_bio(role_id: Optional[str] = None) -> Optional[GlobalBio]:
    """
    获取最新的全局传记信息（包含 shades）
    
    Args:
        role_id: 可选的角色ID，如果不提供则获取最新的全局记录
        
    Returns:
        GlobalBio 对象，如果不存在返回 None
    """
    try:
        db = SessionLocal()
        try:
            # 如果提供了 role_id，获取该角色的 L1 bio
            if role_id:
                # 获取指定角色的最新 L1 bio
                result = db.execute(
                    text("""
                        SELECT content_third_view 
                        FROM l1_bios 
                        WHERE role_id = :role_id
                        ORDER BY version DESC
                        LIMIT 1
                    """),
                    {"role_id": role_id}
                ).fetchone()
            else:
                # 获取最新的全局 L1 bio
                result = db.execute(
                    text("""
                        SELECT content_third_view 
                        FROM l1_bios 
                        WHERE version = (
                            SELECT MAX(version) FROM l1_bios
                        )
                        LIMIT 1
                    """)
                ).fetchone()
            
            if not result or not result[0]:
                return None
            
            content_third_view = result[0]
            
            # 解析 JSON 内容，提取 shades
            try:
                data = json.loads(content_third_view) if isinstance(content_third_view, str) else content_third_view
                # 如果 data 是字典且包含 shades 键
                if isinstance(data, dict) and 'shades' in data:
                    shades = data['shades']
                # 如果 data 本身就是 shades 数组
                elif isinstance(data, list):
                    shades = data
                else:
                    shades = []
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse content_third_view as JSON: {content_third_view[:100]}")
                shades = []
            
            return GlobalBio(shades=shades)
            
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to get latest global bio: {str(e)}", exc_info=True)
        return None


class L1KnowledgeRetriever:
    """L1 knowledge retriever"""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        similarity_threshold: float = 0.7,
        max_shades: int = 3,
    ):
        """
        init L1 knowledge retriever

        Args:
            embedding_service: Embedding service instance
            similarity_threshold: only return contents whose similarity bigger than this value
            max_shades: the maximum number of return shades
        """
        self.embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold
        self.max_shades = max_shades

    def retrieve(self, query: str, role_id: Optional[str] = None) -> str:
        """
        search related L1 shades

        Args:
            query: query content
            role_id: optional role ID to get role-specific global bio

        Returns:
            str: structured knowledge content, or empty string if no relevant knowledge found
        """
        try:
            # get global bio shades
            global_bio = get_latest_global_bio(role_id=role_id)
            if not global_bio or not global_bio.shades:
                logger.info("Global Bio not found or Shades is empty")
                return ""

            # get query embedding
            query_embedding = self.embedding_service.get_embedding(query)
            if not query_embedding:
                logger.error("Failed to get embedding for query text")
                return ""

            # get all shades' embeddings
            shade_embeddings = []
            for shade in global_bio.shades:
                shade_text = (
                    f"{shade.get('title', '')} - {shade.get('description', '')}"
                )
                embedding = self.embedding_service.get_embedding(shade_text)
                if embedding:
                    shade_embeddings.append((shade, embedding))

            if not shade_embeddings:
                logger.info("No available Shades embeddings found")
                return ""

            # calculate similarity and sort
            similar_shades = []
            for shade, embedding in shade_embeddings:
                similarity = self.embedding_service.calculate_similarity(
                    query_embedding, embedding
                )
                if similarity >= self.similarity_threshold:
                    similar_shades.append((shade, similarity))

            # sort according to similarity and limit the number of returned shades
            similar_shades.sort(key=lambda x: x[1], reverse=True)
            similar_shades = similar_shades[: self.max_shades]

            if not similar_shades:
                return ""

            # structured output
            shade_parts = []
            for shade, similarity in similar_shades:
                shade_text = f"Shade: {shade.get('title', '')}\n"
                shade_text += f"Description: {shade.get('description', '')}\n"
                shade_text += f"Similarity: {similarity:.2f}"
                shade_parts.append(shade_text)

            return "\n\n".join(shade_parts)

        except Exception as e:
            logger.error(f"L1 knowledge retrieval failed: {str(e)}")
            return ""


# create default L1 retriever instance
default_l1_retriever = L1KnowledgeRetriever(
    embedding_service=EmbeddingService(), similarity_threshold=0.7, max_shades=3
)

