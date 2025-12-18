from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.status_biography_service import StatusBiographyService
from app.core.response import APIResponse
from app.core.schemas import StatusBiographyRequest
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.put("/status-biography/{role_id}")
def upsert_status_biography(
    role_id: int,  # 根据实际数据库表结构，role_id 是 int4
    request: StatusBiographyRequest,
    db: Session = Depends(get_db)
):
    """
    创建或更新状态传记（upsert）
    
    Args:
        role_id: 角色ID（roles.id，Integer类型）
        request: 状态传记数据（所有字段可选）
        
    Returns:
        APIResponse: 操作结果
    """
    try:
        success, error = StatusBiographyService.update(
            db=db,
            role_id=role_id,
            content=request.content,
            content_third_view=request.content_third_view,
            summary=request.summary,
            summary_third_view=request.summary_third_view
        )
        if not success:
            return APIResponse.error(code=400, message=error)
        return APIResponse.success(message="状态传记保存成功")
    except Exception as e:
        logger.error(f"保存状态传记失败: {str(e)}", exc_info=True)
        return APIResponse.error(code=500, message="保存状态传记失败")


