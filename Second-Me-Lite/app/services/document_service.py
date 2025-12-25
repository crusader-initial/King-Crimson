from sqlalchemy.orm import Session
from app.models.document import Document
from app.services.insight_kernel import InsightKernel
from app.services.summary_kernel import SummaryKernel
from typing import Optional, List, Dict
import logging
import json

logger = logging.getLogger(__name__)

class DocumentService:
    """文档分析服务"""
    
    def __init__(self):
        self.insight_kernel = InsightKernel()
        self.summary_kernel = SummaryKernel()
    
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

    def list_documents_with_l0(self, db: Session) -> List[Dict]:
        """
        get all docs' L0 data
        Args:
            db: 数据库会话
        Returns:
            List[Dict]: list of dict of docs with L0 data
        """
        # 1. get all basic data
        documents = self.list_documents(db)
        logger.info(f"list_documents len: {len(documents)}")

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
        获取文档的嵌入向量
        注意：新表结构中没有 embedding 字段，向量可能存储在其他地方
        Args:
            db: 数据库会话
            document_id: 文档ID
        Returns:
            文档的嵌入向量，如果不存在则返回 None
        """
        # 新表结构中没有 embedding 字段，需要根据实际向量存储位置调整
        # 如果向量存储在其他表，需要从那里查询
        return None

    def get_document_chunks(self, db: Session, document_id: int) -> List:
        """
        获取文档的所有 chunks
        Args:
            db: 数据库会话
            document_id: 文档ID
        Returns:
            chunks 列表
        """
        from app.models.document import Chunk
        return db.query(Chunk).filter(Chunk.document_id == document_id).all()

    def get_chunk_embeddings_by_document_id(self, db: Session, document_id: int) -> Dict[int, List[float]]:
        """
        获取文档所有 chunks 的嵌入向量
        注意：新表结构中没有 embedding 字段，向量可能存储在其他地方
        Args:
            db: 数据库会话
            document_id: 文档ID
        Returns:
            {chunk_id: embedding} 字典
        """
        # 新表结构中没有 embedding 字段，需要根据实际向量存储位置调整
        # 如果向量存储在其他表，需要从那里查询
        return {}

