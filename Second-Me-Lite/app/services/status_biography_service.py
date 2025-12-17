from sqlalchemy.orm import Session
from typing import Optional, Tuple
import logging
from app.models.status_biography import StatusBiography

logger = logging.getLogger(__name__)

class StatusBiographyService:
    """状态传记服务"""
    
    @staticmethod
    def update_content(db: Session, content: str) -> Tuple[bool, Optional[str]]:
        """
        更新状态传记内容
        
        Args:
            db: 数据库会话
            content: 新的内容
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            latest_bio = (
                db.query(StatusBiography)
                .order_by(StatusBiography.create_time.desc())
                .first()
            )
            
            if latest_bio:
                latest_bio.content = content
                logger.info("Updated status_biography.content")
            else:
                # 创建新记录
                new_bio = StatusBiography(
                    content=content,
                    content_third_view=content,
                    summary="",
                    summary_third_view=""
                )
                db.add(new_bio)
                logger.info("Created new status_biography record")
            
            db.commit()
            return True, None
        except Exception as e:
            db.rollback()
            logger.error(f"更新状态传记失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def get_latest_content(db: Session) -> Optional[str]:
        """
        获取最新的状态传记内容
        
        Args:
            db: 数据库会话
            
        Returns:
            内容字符串，如果不存在返回None
        """
        try:
            latest_bio = (
                db.query(StatusBiography)
                .order_by(StatusBiography.create_time.desc())
                .first()
            )
            return latest_bio.content if latest_bio else None
        except Exception as e:
            logger.error(f"获取状态传记失败: {str(e)}", exc_info=True)
            return None

