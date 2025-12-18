from sqlalchemy.orm import Session
from typing import Optional, Tuple
import logging
from app.models.status_biography import StatusBiography
from app.services.load_service import LoadService
from app.services.role_service import RoleService

logger = logging.getLogger(__name__)

class StatusBiographyService:
    """状态传记服务"""
    
    @staticmethod
    def update(
        db: Session,
        role_id: Optional[int] = None,  # 根据实际数据库表结构，role_id 是 int4
        content: Optional[str] = None,
        content_third_view: Optional[str] = None,
        summary: Optional[str] = None,
        summary_third_view: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        更新状态传记记录（按角色ID，可同时更新多个字段）
        
        Args:
            db: 数据库会话
            role_id: 角色ID（可选，如果不提供则自动获取当前用户的角色ID）
            content: 新的内容（可选）
            content_third_view: 新的第三方视角内容（可选）
            summary: 新的摘要（可选）
            summary_third_view: 新的第三方视角摘要（可选）
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            # role_id 必须提供
            if role_id is None:
                return False, "role_id 参数是必需的"
            
            # 查找或创建该角色的状态传记记录
            bio = db.query(StatusBiography).filter(StatusBiography.role_id == role_id).first()
            
            if bio:
                # 更新存在的记录
                if content is not None:
                    bio.content = content
                if content_third_view is not None:
                    bio.content_third_view = content_third_view
                if summary is not None:
                    bio.summary = summary
                if summary_third_view is not None:
                    bio.summary_third_view = summary_third_view
                logger.info(f"Updated status_biography record for role_id={role_id}")
            else:
                # 创建新记录
                new_bio = StatusBiography(
                    role_id=role_id,
                    content=content or "",
                    content_third_view=content_third_view or "",
                    summary=summary or "",
                    summary_third_view=summary_third_view or ""
                )
                db.add(new_bio)
                logger.info(f"Created new status_biography record for role_id={role_id}")
            
            db.commit()
            return True, None
        except Exception as e:
            db.rollback()
            logger.error(f"更新状态传记失败: {str(e)}", exc_info=True)
            return False, str(e)
    

