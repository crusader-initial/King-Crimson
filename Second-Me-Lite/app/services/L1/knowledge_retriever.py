"""
L1知识检索服务
"""
import logging
import json
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from app.services.embedding_service import EmbeddingService
from app.core.database import SessionLocal
from app.models.l1 import L1Shade

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
    """L1知识检索器"""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        similarity_threshold: float = 0.5,
        max_shades: int = 3,
    ):
        """
        初始化L1知识检索器

        Args:
            embedding_service: 嵌入向量服务实例
            similarity_threshold: 仅返回相似度大于此值的内容
            max_shades: 返回shades的最大数量
        """
        self.embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold
        self.max_shades = max_shades

    def retrieve(self, query: str, role_id: Optional[str] = None) -> str:
        """
        搜索相关的L1 shades

        Args:
            query: 查询内容
            role_id: 可选的角色ID，用于获取特定角色的全局传记

        Returns:
            str: 结构化的知识内容，如果未找到相关知识则返回空字符串
        """
        try:
            # 直接查询 l1_shades 表
            if not role_id:
                logger.info("未提供 role_id，无法查询 shades")
                return ""
            
            db = SessionLocal()
            try:
                # 先获取该 role_id 的最新版本号
                max_version_result = db.query(L1Shade.version).filter(
                    L1Shade.role_id == role_id
                ).order_by(L1Shade.version.desc()).first()
                
                if not max_version_result:
                    logger.info(f"未找到 role_id={role_id} 的 Shades")
                    return ""
                
                max_version = max_version_result[0]
                
                # 根据 role_id 和最新版本号查询 shades
                shades = db.query(L1Shade).filter(
                    L1Shade.role_id == role_id,
                    L1Shade.version == max_version
                ).all()
                
                if not shades:
                    logger.info(f"未找到 role_id={role_id} 版本={max_version} 的 Shades")
                    return ""
            finally:
                db.close()

            # 获取查询的嵌入向量
            query_embedding = self.embedding_service.get_embedding(query)
            if not query_embedding:
                logger.error("获取查询文本的嵌入向量失败")
                return ""

            # 获取所有shades的嵌入向量
            shade_embeddings = []
            for shade in shades:
                shade_text = (
                    f"{shade.name or ''} - {shade.desc_third_view or ''}"
                )
                embedding = self.embedding_service.get_embedding(shade_text)
                if embedding:
                    shade_embeddings.append((shade, embedding))

            if not shade_embeddings:
                logger.info("未找到可用的Shades嵌入向量")
                return ""

            # 计算相似度并排序
            similar_shades = []
            for shade, embedding in shade_embeddings:
                similarity = self.embedding_service.calculate_similarity(
                    query_embedding, embedding
                )
                if similarity >= self.similarity_threshold:
                    similar_shades.append((shade, similarity))

            # 根据相似度排序并限制返回的shades数量
            similar_shades.sort(key=lambda x: x[1], reverse=True)
            similar_shades = similar_shades[: self.max_shades]

            if not similar_shades:
                return ""

            # 结构化输出
            shade_parts = []
            for shade, similarity in similar_shades:
                shade_text = f"Shade: {shade.name or ''}\n"
                shade_text += f"Description: {shade.desc_third_view or ''}\n"
                shade_text += f"Similarity: {similarity:.2f}"
                shade_parts.append(shade_text)

            return "\n\n".join(shade_parts)

        except Exception as e:
            logger.error(f"L1知识检索失败: {str(e)}")
            return ""


# 创建默认的L1检索器实例
default_l1_retriever = L1KnowledgeRetriever(
    embedding_service=EmbeddingService(), similarity_threshold=0.7, max_shades=3
)

