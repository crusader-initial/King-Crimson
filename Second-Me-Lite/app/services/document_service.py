from sqlalchemy.orm import Session
from app.models.document import Document, Chunk
from app.services.insight_kernel import InsightKernel
from app.services.summary_kernel import SummaryKernel
from app.services.document_repository import DocumentRepository
from app.services.embedding_service import EmbeddingService, ChunkDTO
from app.services.chunk_service import DocumentChunker, ChunkService
from app.core.config import Config
from typing import Optional, List, Dict
import logging
import json

logger = logging.getLogger(__name__)

class DocumentService:
    """文档分析服务"""
    
    def __init__(self):
        self.insight_kernel = InsightKernel()
        self.summary_kernel = SummaryKernel()
        self._repository = DocumentRepository()
        self.embedding_service = EmbeddingService()
    
    def analyze_document(self, db: Session, document: Document) -> Optional[Document]:
        """
        分析文档
        
        Args:
            db: 数据库会话
            document: 文档对象
        """
        try:
            # 生成 insight（bio_info 在 insight_kernel 内部获取）
            insight_result = self.insight_kernel.analyze(db, document)
            
            # 生成 summary（使用已生成的 insight）
            summary_result = self.summary_kernel.analyze(document, insight_result.get("insight", ""))
            
            # 更新数据库
            document.title = json.dumps(insight_result.get("title", ""),ensure_ascii= False)
            document.insight = json.dumps(insight_result.get("insight", ""), ensure_ascii=False)
            document.summary = json.dumps(summary_result.get("summary", ""), ensure_ascii=False)
            document.keywords = json.dumps(summary_result.get("keywords", []), ensure_ascii=False)
            document.analyze_status = 'SUCCESS'
            
            db.commit()
            db.refresh(document)
            
            logger.info(f"文档分析成功: {document.id}")
            return document
            
        except Exception as e:
            logger.error(f"Error analyzing document {document.id}: {str(e)}", exc_info=True)
            # 更新状态为失败
            self._update_analyze_status_failed(db, document.id)
            raise
    
    def _update_analyze_status_failed(self, db: Session, document_id: int):
        """更新分析状态为失败"""
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.analyze_status = 'FAILED'
                db.commit()
        except Exception as e:
            logger.error(f"更新分析状态失败: {str(e)}", exc_info=True)
    
    def find_unanalyzed_documents(self, db: Session) -> List[Document]:
        """
        查找所有未分析的文档（状态为 INITIALIZED 或 FAILED）
        
        Args:
            db: 数据库会话
            
        Returns:
            List[Document]: 未分析的文档列表
        """
        return db.query(Document).filter(
            Document.analyze_status.in_(['INITIALIZED', 'FAILED'])
        ).all()
    
    def analyze_all_documents(self, db: Session) -> Dict:
        """
        批量分析所有未分析的文档
        
        Args:
            db: 数据库会话
            
        Returns:
            Dict: 包含成功和失败统计的结果
                - total: 总文档数
                - success: 成功分析的文档列表
                - failed: 失败的文档列表
                - success_count: 成功数量
                - failed_count: 失败数量
        """
        unanalyzed_docs = self.find_unanalyzed_documents(db)
        
        results = {
            "total": len(unanalyzed_docs),
            "success": [],
            "failed": [],
            "success_count": 0,
            "failed_count": 0
        }
        
        if results["total"] == 0:
            logger.info("没有需要分析的文档")
            return results
        
        logger.info(f"开始批量分析 {results['total']} 个文档")
        
        for doc in unanalyzed_docs:
            try:
                # 直接传递 Document 对象，避免重复查询
                analyzed_doc = self.analyze_document(db, doc)
                results["success"].append({
                    "id": analyzed_doc.id,
                    "name": analyzed_doc.name,
                    "analyze_status": analyzed_doc.analyze_status
                })
                results["success_count"] += 1
                logger.info(f"文档 {doc.id} ({doc.name}) 分析成功")
            except Exception as e:
                results["failed"].append({
                    "id": doc.id,
                    "name": doc.name,
                    "error": str(e)
                })
                results["failed_count"] += 1
                logger.error(f"文档 {doc.id} ({doc.name}) 分析失败: {str(e)}")
                continue
        
        logger.info(f"批量分析完成：成功 {results['success_count']} 个，失败 {results['failed_count']} 个")
        return results
    
    def list_documents(self, db: Session) -> List[Document]:
        """
        get all doc list
        Args:
            db: 数据库会话
        Returns:
            List[Document]: doc object list
        """
        return db.query(Document).all()

    def list_documents_with_l0(self, db: Session, role_id: Optional[str] = None) -> List[Dict]:
        """
        get all docs' L0 data
        Args:
            db: 数据库会话
            role_id: 可选的角色ID，如果提供则只返回该角色的文档
        Returns:
            List[Dict]: list of dict of docs with L0 data
        """
        # 1. get all basic data
        if role_id:
            documents = db.query(Document).filter(Document.role_id == role_id).all()
        else:
            documents = self.list_documents(db)
        logger.info(f"list_documents len: {len(documents)}" + (f" (role_id={role_id})" if role_id else ""))

        # 2. each doc L0
        documents_with_l0 = []
        for doc in documents:
            # 将 Document 对象转换为字典
            doc_dict = {
                "id": doc.id,
                "name": doc.name,
                "title": doc.title,
                "mime_type": doc.mime_type,
                "raw_content": doc.raw_content,
                "create_time": doc.create_time,
                "update_time": doc.update_time,
                "insight": doc.insight,
                "summary": doc.summary,
                "keywords": doc.keywords,
                "role_id": doc.role_id,
            }
            # L0 数据已经在 insight 和 summary 字段中，不需要单独获取
            documents_with_l0.append(doc_dict)

        return documents_with_l0

    def get_document_embedding(self, db: Session, document_id: int) -> Optional[List[float]]:
        """
        get doc embedding
        Args:
            db: 数据库会话
            document_id (int): doc ID
        Returns:
            Optional[List[float]]: doc embedding
        Raises:
            Exception: error occurred
        """
        try:
            from app.core.vector import get_document_embedding as _get_document_embedding
            return _get_document_embedding(db, document_id)
        except Exception as e:
            logger.error(f"Error getting document embedding: {str(e)}")
            raise

    def get_document_chunks(self, db: Session, document_id: int) -> List[ChunkDTO]:
        """
        get chunks result
        Args:
            db: 数据库会话（保留以保持兼容性，但当前实现不使用）
            document_id (int): doc ID
        Returns:
            List[ChunkDTO]: doc chunks list，each ChunkDTO include embedding info
        """
        try:
            document = self._repository.find_one(document_id=document_id)
            if not document:
                logger.info(f"Document not found with id: {document_id}")
                return []

            chunks = self._repository.find_chunks(document_id=document_id)
            logger.info(f"Found {len(chunks)} chunks for document {document_id}")

            for chunk in chunks:
                chunk.length = len(chunk.content) if chunk.content else 0
                if chunk.has_embedding:
                    chunk.embedding = (
                        self.embedding_service.get_chunk_embedding_by_chunk_id(chunk.id)
                    )

            return chunks

        except Exception as e:
            logger.error(f"Error getting chunks for document {document_id}: {str(e)}")
            return []

    def get_chunk_embeddings_by_document_id(self, db: Session, document_id: int) -> Dict[int, List[float]]:
        """
        获取文档所有 chunks 的嵌入向量（从 pgvector 的 chunk_embedding 表读取）
        Args:
            db: 数据库会话
            document_id: 文档ID
        Returns:
            {chunk_id: embedding} 字典
        """
        from app.core.vector import get_chunk_embedding
        from app.models.document import Chunk
        
        # 获取文档的所有 chunks
        chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
        
        # 从 pgvector 读取每个 chunk 的向量
        chunk_embeddings = {}
        for chunk in chunks:
            embedding = get_chunk_embedding(db, chunk.id)
            if embedding:
                chunk_embeddings[chunk.id] = embedding
        
        return chunk_embeddings

    def process_document_chunks(self, db: Session, document_id: int) -> int:
        """
        处理文档分块：将文档内容分割成 chunks 并保存到数据库
        
        Args:
            db: 数据库会话
            document_id: 文档ID
            
        Returns:
            int: 创建的 chunks 数量
            
        Raises:
            ValueError: 文档不存在或没有内容
            Exception: 处理失败
        """
        try:
            document = self._repository.find_one(document_id=document_id)
            if not document:
                raise ValueError(f"Document not found with id: {document_id}")
            
            if not document.raw_content:
                logger.warning(f"Document {document_id} has no content to process chunks")
                raise ValueError(f"Document {document_id} has no content")
            
            # 获取配置
            config = Config.from_env()
            chunker = DocumentChunker(
                chunk_size=int(config.get("DOCUMENT_CHUNK_SIZE", 500)),
                overlap=int(config.get("DOCUMENT_CHUNK_OVERLAP", 50)),
            )
            
            # 分割成 chunks
            chunks = chunker.split(document.raw_content)
            
            # 保存 chunks
            chunk_service = ChunkService()
            for chunk in chunks:
                chunk.document_id = document_id
                chunk_service.save_chunk(chunk)
            
            # 提交更改
            db.commit()
            
            logger.info(f"Document {document_id} processed: created {len(chunks)} chunks")
            return len(chunks)
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error processing document chunks for document {document_id}: {str(e)}")
            db.rollback()
            raise

    def generate_document_chunk_embeddings(self, document_id: int) -> List[ChunkDTO]:
        """
        handle chunks and embeddings
        Args:
            document_id (int): ID
        Returns:
            List[ChunkDTO]: chunks list
        Raises:
            Exception: error occurred
        """
        try:
            chunks_dtos = self._repository.find_chunks(document_id)
            if not chunks_dtos:
                logger.info(f"No chunks found for document {document_id}")
                return []

            # handle embeddings (store_embedding 已经更新了数据库中的 has_embedding 状态)
            processed_chunks = self.embedding_service.generate_chunk_embeddings(
                chunks_dtos
            )

            # Update document embedding status
            all_processed = all(c.has_embedding for c in processed_chunks)
            if all_processed and processed_chunks:
                self._repository.update_embedding_status(document_id, 'SUCCESS')
            else:
                self._repository.update_embedding_status(document_id, 'INITIALIZED')

            return processed_chunks

        except Exception as e:
            logger.error(f"Error processing chunk embeddings: {str(e)}")
            # Update document status to failed
            try:
                self._repository.update_embedding_status(document_id, 'FAILED')
            except:
                pass
            raise

    def process_document_embedding(self, document_id: int) -> Optional[List[float]]:
        """
        handle doc level embedding
        Args:
            document_id (int): doc ID
        Returns:
            Optional[List[float]]: doc embedding
        Raises:
            ValueError: doc not exist
            Exception: error occurred
        """
        try:
            document = self._repository.find_one(document_id)
            if not document:
                raise ValueError(f"Document not found with id: {document_id}")

            if not document.raw_content:
                logger.warning(
                    f"Document {document_id} has no content to process embedding"
                )
                self._repository.update_embedding_status(
                    document_id, 'FAILED'
                )
                return None

            # gen doc embedding
            embedding = self.embedding_service.generate_document_embedding(document)
            if embedding is not None:
                self._repository.update_embedding_status(
                    document_id, 'SUCCESS'
                )
            else:
                self._repository.update_embedding_status(
                    document_id, 'FAILED'
                )

            return embedding

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error processing document embedding: {str(e)}")
            self._repository.update_embedding_status(document_id, 'FAILED')
            raise

