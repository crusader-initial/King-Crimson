from typing import List, Optional, Dict
from sqlalchemy import select
from app.services.embedding_service import ChunkDTO
from app.models.document import Chunk, Document
from app.core.database import DatabaseSession
import logging

logger = logging.getLogger(__name__)


# 定义 BaseRepository 基类
class BaseRepository:
    """基础 Repository 类"""
    def __init__(self, model):
        self.model = model
        self._db = DatabaseSession()


# 注意：直接使用 Document 模型，不需要 DTO
# DTO 通常用于：
# 1. 跨服务边界传输数据（微服务架构）
# 2. 隐藏数据库模型细节（API 层）
# 3. 序列化/反序列化特殊需求
# 在这个项目中，直接使用 SQLAlchemy 模型更简单高效


class DocumentRepository(BaseRepository):
    def __init__(self):
        super().__init__(Document)

    def update_document_analysis(
        self, doc_id: int, insight: Dict, summary: Dict
    ) -> Optional[Document]:
        """update doc's insight and summary"""
        with self._db.session() as session:
            document = session.get(self.model, doc_id)
            if document:
                document.insight = insight
                document.summary = summary
                document.analyze_status = 'SUCCESS'
                session.commit()
                return document
            return None

    def find_unanalyzed(self) -> List[Document]:
        """search unanalyzed doc according to analyze_status"""
        with self._db.session() as session:
            query = select(self.model).where(
                self.model.analyze_status.in_(['INITIALIZED', 'FAILED'])
            )
            result = session.execute(query)
            return list(result.scalars().all())

    def find_chunks(self, document_id: int) -> List[ChunkDTO]:
        """search all chunks of the specified document"""
        with self._db.session() as session:
            chunks = (
                session.query(Chunk)
                .filter(Chunk.document_id == document_id)
                .all()
            )
            return [
                ChunkDTO(
                    id=chunk.id,
                    content=chunk.content,
                    document_id=chunk.document_id,
                    tags=chunk.tags,
                    topic=chunk.topic,
                    has_embedding=chunk.has_embedding,
                )
                for chunk in chunks
            ]

    def save_chunk(self, chunk: Chunk) -> Chunk:
        """save chunk"""
        with self._db.session() as session:
            session.add(chunk)
            session.flush()  # get auto-gen ID
            session.refresh(chunk)
            return chunk

    def find_one(self, document_id: int) -> Optional[Document]:
        """search doc by id"""
        with self._db.session() as session:
            # 使用 query 而不是 get，确保所有列都被加载
            document = session.query(self.model).filter(self.model.id == document_id).first()
            if document:
                # 在会话关闭前预加载所有需要的属性，避免 DetachedInstanceError
                # 通过访问属性触发加载，确保数据在会话内加载完成
                _ = document.raw_content
                # 将对象从 Session 中分离，但保留已加载的数据
                # 这样对象可以在 Session 关闭后继续使用
                session.expunge(document)
            return document

    def update_chunk_embedding_status(self, chunk_id: int, has_embedding: bool) -> None:
        """update chunk embedding"""
        try:
            with self._db.session() as session:
                chunk = (
                    session.query(Chunk).filter(Chunk.id == chunk_id).first()
                )
                if chunk:
                    chunk.has_embedding = has_embedding
                    session.commit()
                    logger.debug(f"Updated embedding status for chunk {chunk_id}")
                else:
                    logger.warning(f"Chunk not found with id: {chunk_id}")
        except Exception as e:
            logger.error(f"Error updating chunk embedding status: {str(e)}")
            raise

    def find_unembedding(self) -> List[Document]:
        """search unembedding documents according to embedding_status"""
        with self._db.session() as session:
            query = select(self.model).where(
                self.model.embedding_status.in_(['INITIALIZED', 'FAILED'])
            )
            result = session.execute(query)
            return list(result.scalars().all())

    def update_embedding_status(self, document_id: int, status: str) -> None:
        """update doc embedding"""
        try:
            with self._db.session() as session:
                document = (
                    session.query(self.model)
                    .filter(self.model.id == document_id)
                    .first()
                )
                if document:
                    document.embedding_status = status
                    session.commit()
                    logger.debug(
                        f"Updated embedding status for document {document_id} to {status}"
                    )
                else:
                    logger.warning(f"Document not found with id: {document_id}")
        except Exception as e:
            logger.error(f"Error updating document embedding status: {str(e)}")
            raise
