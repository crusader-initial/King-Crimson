from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.status_biography import StatusBiography
from app.models.load import Load
from app.services.insight_kernel import InsightKernel
from app.services.summary_kernel import SummaryKernel
from app.services.load_service import LoadService
from app.services.role_service import RoleService
from app.core.schemas import BioInfo
from typing import Optional
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
            # 1. 获取文档
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"文档不存在: {document_id}")
            
            # 2. 获取 BioInfo（根据文档关联的 role_id）
            bio_info = self._get_bio_info(db, document)
            
            # 3. 生成 Insight（两阶段）
            insight_text, title, insight_json = self.insight_kernel.analyze(document, bio_info)
            
            # 4. 生成 Summary（使用已生成的 insight）
            summary_result = self.summary_kernel.analyze(document, insight_text)
            
            # 5. 更新数据库
            document.insight = json.dumps(insight_json, ensure_ascii=False)
            document.summary = json.dumps(summary_result, ensure_ascii=False)
            document.keywords = json.dumps(summary_result.get("keywords", []), ensure_ascii=False)
            document.analyze_status = 'SUCCESS'
            
            db.commit()
            db.refresh(document)
            
            logger.info(f"文档分析成功: {document_id}")
            return document
            
        except ValueError as e:
            logger.error(f"文档不存在: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"分析文档失败: {str(e)}", exc_info=True)
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
            
            role_id = document.role_id  # role_id 是 Integer 类型
            
            # 1. 获取状态传记（从 status_biography 表）
            status_bio = db.query(StatusBiography).filter(
                StatusBiography.role_id == role_id
            ).first()
            
            # 2. 获取角色信息（从 role 表）
            from app.models.role import Role
            role = db.query(Role).filter(Role.id == role_id).first()  # role.id 是 Integer 类型
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

