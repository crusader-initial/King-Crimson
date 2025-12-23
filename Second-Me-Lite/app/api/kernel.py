from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.response import APIResponse
from app.core.utils import serialize_value
from app.services.L1.l1_manager import generate_l1_from_l0, store_l1_data
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/l1/global/generate")
def generate_l1(db: Session = Depends(get_db)):
    """Generate L1 data from L0 data and store
    
    Returns:
        APIResponse with version number and generated data
    """
    try:
        # 1. Generate L1 data
        result = generate_l1_from_l0()

        if result is None:
            return APIResponse.error("No valid L1 data generated")

        # 2. Store L1 data
        # 使用从文档中提取的 role_id，如果为 None 则使用默认值或报错
        role_id = result.role_id
        if not role_id:
            logger.warning("未找到有效的 role_id，L1 数据可能无法正确存储")
        version_number = store_l1_data(db, result, role_id=role_id)

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

