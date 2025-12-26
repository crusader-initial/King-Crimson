"""
嵌入向量服务，用于处理嵌入向量和相似度搜索
"""
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from app.core.vector import (
    get_embedding as _get_embedding, 
    search_similar_chunks as _search_similar_chunks, 
    store_embedding as _store_embedding, 
    get_embeddings_batch as _get_embeddings_batch,
    get_embedding_with_chunking as _get_embedding_with_chunking,
    store_document_embedding as _store_document_embedding,
    get_document_embedding as _get_document_embedding,
    store_embeddings_batch as _store_embeddings_batch,
    get_chunk_embedding as _get_chunk_embedding
)
from app.core.database import SessionLocal
from app.models.document import Document
import numpy as np
import logging

logger = logging.getLogger(__name__)


class ChunkDTO:
    """Chunk 数据传输对象"""
    def __init__(self, id: int, content: str, document_id: Optional[int] = None, 
                 tags: Optional[str] = None, topic: Optional[str] = None, 
                 has_embedding: bool = False):
        self.id = id
        self.content = content
        self.document_id = document_id
        self.tags = tags
        self.topic = topic
        self.has_embedding = has_embedding


class EmbeddingService:
    """嵌入向量服务，用于处理嵌入向量和相似度搜索"""
    
    def __init__(self, db: Optional[Session] = None):
        """
        初始化 EmbeddingService
        
        Args:
            db: 可选的数据库会话。如果未提供，将在需要时创建新会话。
        """
        self._db = db
    
    def _get_db(self) -> Session:
        """获取数据库会话"""
        if self._db:
            return self._db
        return SessionLocal()
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        获取文本的嵌入向量
        
        Args:
            text: 要嵌入的文本
            
        Returns:
            嵌入向量，如果失败则返回 None
        """
        try:
            return _get_embedding(text)
        except Exception as e:
            logger.error(f"Failed to get embedding: {str(e)}")
            return None
    
    def search_similar_chunks(self, query: str, limit: int = 3) -> List[Tuple[ChunkDTO, float]]:
        """
        搜索相似的 chunks
        
        Args:
            query: 查询文本
            limit: 最大返回结果数量
            
        Returns:
            元组列表 (ChunkDTO, similarity_score)
        """
        db = self._get_db()
        try:
            # 获取查询的嵌入向量
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                logger.error("Failed to get embedding for query")
                return []
            
            # 搜索相似的 chunks
            results = _search_similar_chunks(db, query_embedding, limit)
            
            # 转换为 ChunkDTO 元组
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
            # 仅在我们创建的会话时关闭
            if not self._db:
                db.close()
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        计算两个嵌入向量之间的余弦相似度
        
        Args:
            embedding1: 第一个嵌入向量
            embedding2: 第二个嵌入向量
            
        Returns:
            余弦相似度分数 (0-1)
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # 计算余弦相似度
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
    
    def get_chunk_embedding_by_chunk_id(self, chunk_id: int) -> Optional[List[float]]:
        """
        根据 chunk ID 从 pgvector 获取 chunk 的嵌入向量
        Args:
            chunk_id (int): chunk ID
        Returns:
            Optional[List[float]]: chunk 的嵌入向量
        Raises:
            Exception: 发生错误时抛出异常
        """
        db = self._get_db()
        try:
            embedding = _get_chunk_embedding(db, chunk_id)
            return embedding
        except Exception as e:
            logger.error(f"Error getting chunk embedding: {str(e)}")
            raise
        finally:
            # 仅在我们创建的会话时关闭
            if not self._db:
                db.close()

    def generate_chunk_embeddings(self, chunks: List[ChunkDTO]) -> List[ChunkDTO]:
        """
        处理 chunk 级别的嵌入向量
        批量处理 chunks 的 embeddings，参考批量处理思路但使用项目现有技术栈
        
        Args:
            chunks: 要处理的 ChunkDTO 对象列表
            
        Returns:
            List[ChunkDTO]: 处理后的 chunks，has_embedding 状态已更新
        """
        try:
            # 筛选出未处理的 chunks
            unprocessed_chunks = [c for c in chunks if not c.has_embedding]
            if not unprocessed_chunks:
                logger.info("No unprocessed chunks found")
                return chunks

            logger.info(f"Processing embeddings for {len(unprocessed_chunks)} chunks")

            # 批量获取 embeddings
            contents = [c.content for c in unprocessed_chunks]
            logger.info(f"Getting embeddings from local model for {len(contents)} chunks...")
            
            try:
                embeddings = _get_embeddings_batch(contents)
                
                if embeddings is None or len(embeddings) == 0:
                    logger.error("Failed to get embeddings from model")
                    return chunks

                logger.info(f"Successfully got embeddings with shape: {embeddings.shape}")

                # 批量存储到数据库（pgvector）
                db = self._get_db()
                try:
                    logger.info("Storing embeddings to pgvector...")
                    
                    # 批量存储向量到 chunk_embedding 表
                    chunk_ids = [c.id for c in unprocessed_chunks]
                    _store_embeddings_batch(db, chunk_ids, embeddings)
                    
                    logger.info("Successfully stored embeddings to pgvector")

                    # 验证 embeddings 存储
                    from app.models.document import Chunk
                    for i, chunk in enumerate(unprocessed_chunks):
                        try:
                            # 查询数据库验证 has_embedding 状态
                            stored_chunk = db.query(Chunk).filter(Chunk.id == chunk.id).first()
                            # 验证向量是否存储在 pgvector 中
                            stored_embedding = _get_chunk_embedding(db, chunk.id)
                            
                            if stored_chunk and stored_chunk.has_embedding and stored_embedding:
                                chunk.has_embedding = True
                                logger.debug(f"Verified embedding for chunk {chunk.id} (stored in pgvector)")
                            else:
                                logger.warning(f"Failed to verify embedding for chunk {chunk.id}")
                                chunk.has_embedding = False
                        except Exception as e:
                            logger.warning(f"Error verifying embedding for chunk {chunk.id}: {str(e)}")
                            chunk.has_embedding = False

                except Exception as e:
                    logger.error(f"Error storing embeddings in database: {str(e)}", exc_info=True)
                    for chunk in unprocessed_chunks:
                        chunk.has_embedding = False
                    raise
                finally:
                    # 仅在我们创建的会话时关闭
                    if not self._db:
                        db.close()

            except Exception as e:
                logger.error(f"Error generating embeddings: {str(e)}", exc_info=True)
                for chunk in unprocessed_chunks:
                    chunk.has_embedding = False
                raise

            return chunks

        except Exception as e:
            logger.error(f"Error processing chunk embeddings: {str(e)}", exc_info=True)
            raise

    def generate_document_embedding(self, document: Document) -> Optional[List[float]]:
        """
        处理文档级别的嵌入向量并存储到 pgvector
        参考逻辑：检查文档内容 -> 生成 embedding（处理长文本分块） -> 存储到 pgvector -> 验证存储
        
        Args:
            document: Document 对象（SQLAlchemy 模型）
            
        Returns:
            Optional[List[float]]: 文档的嵌入向量，如果失败则返回 None
        """
        try:
            if not document.raw_content:
                logger.warning(
                    f"Document {document.id} has no content to process embedding"
                )
                return None

            # 生成 embedding（处理长文本分块）
            logger.info(f"Generating embedding for document {document.id}")
            
            # 使用带分块处理的函数，处理超长文本
            # bge-m3 最大支持 8192 tokens，但为了性能，我们使用较小的 chunk_size
            # 如果文本超过 max_text_length（字符数），会自动分块并求平均
            embedding = _get_embedding_with_chunking(
                document.raw_content,
                max_text_length=8192 * 4,  # 大约 8192 tokens 对应的字符数（粗略估算）
                chunk_size=512  # 每个分块的最大 token 长度
            )

            if embedding is None or len(embedding) == 0:
                logger.error(f"Failed to get embedding for document {document.id}")
                return None

            logger.info(f"Successfully got embedding for document {document.id} (dimension: {len(embedding)})")

            # 存储到 pgvector
            db = self._get_db()
            try:
                logger.info(f"Storing embedding for document {document.id} in pgvector")
                _store_document_embedding(db, document.id, embedding)
                logger.info(f"Successfully stored embedding for document {document.id}")

                # 验证 embedding 存储
                stored_embedding = _get_document_embedding(db, document.id)
                if not stored_embedding or len(stored_embedding) == 0:
                    logger.error(
                        f"Failed to verify embedding storage for document {document.id}"
                    )
                    return None
                
                logger.info(f"Verified embedding storage for document {document.id}")
                return embedding

            except Exception as e:
                logger.error(f"Error storing document embedding in pgvector: {str(e)}", exc_info=True)
                return None
            finally:
                # 仅在我们创建的会话时关闭
                if not self._db:
                    db.close()

        except Exception as e:
            logger.error(f"Error processing document embedding: {str(e)}", exc_info=True)
            raise

