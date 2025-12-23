from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.status_biography import StatusBiography
from app.models.load import Load
from app.services.insight_kernel import InsightKernel
from app.services.summary_kernel import SummaryKernel
from app.services.load_service import LoadService
from app.services.role_service import RoleService
from app.core.schemas import BioInfo
from typing import Optional, List, Dict
import logging
import json

logger = logging.getLogger(__name__)

class DocumentService:
    """文档分析服务"""
    
    def __init__(self):
        self.insight_kernel = InsightKernel()
        self.summary_kernel = SummaryKernel()
    
    def analyze_document(self, db: Session, document_id: int) -> Optional[Document]:
        """
        分析文档
        
        Args:
            db: 数据库会话
            document_id: 文档ID
            
        Returns:
            Document: 分析后的文档对象
            
        Raises:
            ValueError: 文档不存在
            Exception: 分析失败
        """
        try:
            # 获取文档
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document not found with id: {document_id}")
            
            # 获取 BioInfo（根据文档关联的 role_id）
            bio_info = self._get_bio_info(db, document)
            
            # 生成 insight
            insight_text, title, insight_json = self.insight_kernel.analyze(document, bio_info)
            
            # 生成 summary（使用已生成的 insight）
            summary_result = self.summary_kernel.analyze(document, insight_text)
            
            # 更新数据库
            document.insight = json.dumps(insight_json, ensure_ascii=False)
            document.summary = json.dumps(summary_result, ensure_ascii=False)
            document.keywords = json.dumps(summary_result.get("keywords", []), ensure_ascii=False)
            document.analyze_status = 'SUCCESS'
            
            db.commit()
            db.refresh(document)
            
            logger.info(f"文档分析成功: {document_id}")
            return document
            
        except ValueError as e:
            logger.error(f"Document {document_id} not found: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error analyzing document {document_id}: {str(e)}", exc_info=True)
            # 更新状态为失败
            self._update_analyze_status_failed(db, document_id)
            raise
    
    def _get_bio_info(self, db: Session, document: Document) -> BioInfo:
        """
        获取用户传记信息（根据文档关联的 role_id）
        从 status_biography 和 role 表中获取数据
        
        Args:
            db: 数据库会话
            document: 文档对象
            
        Returns:
            BioInfo: 用户传记信息
        """
        try:
            # 从文档获取 role_id
            if not document.role_id:
                logger.warning(f"文档 {document.id} 未关联角色，返回空的 BioInfo")
                return BioInfo()
            
            role_id = document.role_id  # document.role_id 是 Integer 类型
            
            # 1. 获取状态传记（从 status_biography 表）
            # 注意：status_biography.role_id 是 varchar(36)，需要转换为字符串进行比较
            status_bio = db.query(StatusBiography).filter(
                StatusBiography.role_id == str(role_id)
            ).first()
            
            # 2. 获取角色信息（从 role 表）
            from app.models.role import Role
            role = db.query(Role).filter(Role.id == str(role_id)).first()  # role.id 是 String(36) 类型
            if not role:
                logger.warning(f"未找到角色 {role_id}，返回空的 BioInfo")
                return BioInfo()
            
            # 3. 构建 BioInfo（所有字段都从 status_biography 和 role 表中获取）
            global_bio = status_bio.content_third_view if status_bio else ""
            status_bio_content = status_bio.content if status_bio else ""
            about_me = role.description or ""  # 从 role.description 获取，不是 loads.description
            
            logger.info(f"成功获取文档 {document.id} 的 BioInfo，role_id: {role_id}")
            return BioInfo(
                global_bio=global_bio,
                status_bio=status_bio_content,
                about_me=about_me
            )
            
        except Exception as e:
            logger.error(f"获取 BioInfo 失败: {str(e)}", exc_info=True)
            return BioInfo()
    
    def _update_analyze_status_failed(self, db: Session, document_id: int):
        """更新分析状态为失败"""
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.analyze_status = 'FAILED'
                db.commit()
        except Exception as e:
            logger.error(f"更新分析状态失败: {str(e)}", exc_info=True)
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
        Args:
            db: 数据库会话
            document_id: 文档ID
        Returns:
            文档的嵌入向量，如果不存在则返回 None
        """
        # 注意：Document 模型可能没有 embedding 字段，需要根据实际情况调整
        # 这里假设从 chunks 中获取第一个 chunk 的 embedding 作为文档 embedding
        from app.models.document import Chunk
        chunk = db.query(Chunk).filter(Chunk.document_id == document_id).first()
        if chunk is not None and chunk.embedding is not None:
            return chunk.embedding.tolist() if hasattr(chunk.embedding, 'tolist') else list(chunk.embedding)
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
        Args:
            db: 数据库会话
            document_id: 文档ID
        Returns:
            {chunk_id: embedding} 字典
        """
        from app.models.document import Chunk
        chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
        embeddings = {}
        for chunk in chunks:
            if chunk is not None and chunk.embedding is not None:
                embedding = chunk.embedding.tolist() if hasattr(chunk.embedding, 'tolist') else list(chunk.embedding)
                embeddings[chunk.id] = embedding
        return embeddings

