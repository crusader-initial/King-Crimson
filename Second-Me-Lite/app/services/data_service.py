from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Optional
import logging
from app.models.load import Load
from app.services.status_biography_service import StatusBiographyService

logger = logging.getLogger(__name__)

def get_user_data(db: Session) -> Dict[str, Optional[str]]:
    """
    获取三个字段的数据
    
    Args:
        db: 数据库会话
        
    Returns:
        包含三个字段的字典:
        {
            "l1_bio_content_third_view": ...,
            "status_bio_content": ...,
            "load_description": ...
        }
    """
    result = {
        "l1_bio_content_third_view": None,
        "status_bio_content": None,
        "load_description": None
    }
    
    # 1. 获取 loads.description
    try:
        current_load = db.query(Load).first()
        if current_load:
            result["load_description"] = current_load.description
    except Exception as e:
        logger.warning(f"获取loads.description失败: {str(e)}")
    
    # 2. 获取 status_biography.content
    try:
        result["status_bio_content"] = StatusBiographyService.get_latest_content(db)
    except Exception as e:
        logger.warning(f"获取status_biography.content失败: {str(e)}")
    
    # 3. 获取 l1_bios.content_third_view
    try:
        result_query = db.execute(
            text("""
                SELECT content_third_view 
                FROM l1_bios 
                WHERE version = (
                    SELECT MAX(version) FROM l1_bios
                )
                LIMIT 1
            """)
        ).fetchone()
        
        if result_query:
            result["l1_bio_content_third_view"] = result_query[0]
    except Exception as e:
        logger.warning(f"获取l1_bios.content_third_view失败: {str(e)}")
    
    return result

