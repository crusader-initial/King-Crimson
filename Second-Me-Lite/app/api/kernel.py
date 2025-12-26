from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.response import APIResponse
from app.core.utils import serialize_value
from app.core.schemas import GenerateStatusBioRequest, GenerateL1Request
from app.services.L1.l1_manager import generate_l1_from_l0, store_l1_data, generate_and_store_status_bio
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/l1/global/generate")
def generate_l1(request: GenerateL1Request, db: Session = Depends(get_db)):
    """Generate L1 data from L0 data and store
    
    Args:
        request: 包含 role_id 的请求对象
        db: 数据库会话
    
    Returns:
        APIResponse with version number and generated data
    """
    try:
        # 1. Generate L1 data
        result = generate_l1_from_l0(role_id=request.role_id)

        if result is None:
            return APIResponse.error("No valid L1 data generated")

        # 2. Store L1 data
        # 使用请求中传入的 role_id
        version_number = store_l1_data(db, result, role_id=request.role_id)

        # 3. Convert result to serializable format
        serializable_result = serialize_value(result.to_dict())

        # 4. Return the result
        response_data = {
            "version": version_number,
            "message": f"L1 数据已成功生成并存储，版本为 {version_number}",
            "data": serializable_result,
        }

        return APIResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"Error generating L1: {str(e)}", exc_info=True)
        return APIResponse.error(code=500, message=str(e))


@router.post("/l1/status_bio/generate")
def generate_status_biography(request: GenerateStatusBioRequest):
    """Generate status biography for a specific role
    
    Args:
        request: 包含 role_id 的请求对象
    """
    try:
        # Call l1_manager method to generate and store status biography
        status_bio = generate_and_store_status_bio(role_id=request.role_id)

        if status_bio is None:
            return APIResponse.error(code=500, message=f"状态传记生成失败 (role_id={request.role_id})")

        # Build response data
        response_data = {
            "content": status_bio.content_second_view,
            "content_third_view": status_bio.content_third_view,
            "summary": status_bio.summary_second_view,
            "summary_third_view": status_bio.summary_third_view,
            "shades": [
                {
                    "name": shade.name,
                    "aspect": shade.aspect,
                    "icon": shade.icon,
                    "desc_third_view": shade.desc_third_view,
                    "content_third_view": shade.content_third_view,
                    "desc_second_view": shade.desc_second_view,
                    "content_second_view": shade.content_second_view,
                }
                for shade in status_bio.shades_list
            ],
        }

        return APIResponse.success(data=response_data)
    
    except Exception as e:
        logger.error(f"Error generating status biography: {str(e)}", exc_info=True)
        return APIResponse.error(code=500, message=f"生成状态传记失败: {str(e)}")

