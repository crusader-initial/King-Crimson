from app.services.L0.l0_generator import L0Generator
from app.core.schemas import FileInfo, BioInfo, InsighterInput
from app.models.document import Document
from app.models.status_biography import StatusBiography
from sqlalchemy.orm import Session
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class InsightKernel:
    """Insight 生成内核"""
    
    def __init__(self):
        self.generator = L0Generator()
        self.preferred_language = "zh_CN"  # 默认使用中文语言
    
    def analyze(self, db: Session, doc: Document) -> Dict:
        """
        生成文档 insight
        
        Args:
            db: 数据库会话
            doc: Document 对象
            
        Returns:
            Dict: 包含 title 和 insight 的字典
        """
        try:
            self.generator.preferred_language = self.preferred_language
            
            # # 获取 BioInfo（根据文档关联的 role_id）
            # bio_info = self._get_bio_info(db, doc)
            
            # 使用空的 BioInfo（暂时不获取用户传记信息）
            bio_info = BioInfo()
            
            # 构建 FileInfo
            file_info = FileInfo(
                data_type=doc.mime_type,
                filename=doc.name,
                content= "",
                file_content={"content": doc.raw_content}
            )
            
            # 构建 InsighterInput
            insighter_input = InsighterInput(file_info=file_info,bio_info=bio_info)
            
            # 调用 LLM 生成 insight（两阶段）
            insight_result = self.generator.insighter(insighter_input)
            
            return {
                "title": insight_result.get("title"),
                "insight": insight_result.get("insight"),
            }
            
        except Exception as e:
            logger.error(f"生成 insight 失败: {str(e)}", exc_info=True)
            raise Exception(f"生成 insight 失败: {e}")
    
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

