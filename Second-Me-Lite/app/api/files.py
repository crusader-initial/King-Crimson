from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.services.file_service import FileService
from app.services.document_service import DocumentService
from app.core.response import APIResponse
import json
import logging
from urllib.parse import unquote

router = APIRouter()
logger = logging.getLogger(__name__)

file_service = FileService()
document_service = DocumentService()

@router.post("/file")
def upload_file(
    file: UploadFile = File(...),
    metadata: str = Form(None),
    role_id: Optional[str] = Form(None),  # 从 Form 参数获取 role_id
    db: Session = Depends(get_db)
):
    """
    文件上传接口
    
    支持从 Form 参数 role_id 获取用户ID，或从 metadata 中获取
    """
    # 解析元数据
    metadata_dict = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except:
            pass
    
    # 优先从 Form 参数获取，其次从 metadata 获取
    user_role_id = role_id or metadata_dict.get('role_id') or metadata_dict.get('load_id') or metadata_dict.get('user_id')
    
    return file_service.upload_file(db, file, metadata_dict, user_role_id)

@router.delete("/file/{filename}")
def delete_file(
    filename: str,
    db: Session = Depends(get_db)
):
    """
    文件删除接口
    """
    # URL 解码文件名（处理中文等特殊字符）
    decoded_filename = unquote(filename)
    return file_service.delete_file(db, decoded_filename)

@router.post("/documents/{document_id}/analyze")
def analyze_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    分析文档接口
    
    Args:
        document_id: 文档ID（路径参数）
        
    Returns:
        APIResponse: 分析结果，包含完整的分析数据
    """
    try:
        document = document_service.analyze_document(db, document_id)
        return APIResponse.success(
            data={
                "id": document.id,
                "name": document.name,
                "analyze_status": document.analyze_status,
                "insight": document.insight,
                "summary": document.summary,
                "keywords": document.keywords
            },
            message="文档分析成功"
        )
    except ValueError as e:
        return APIResponse.error(code=404, message=str(e))
    except Exception as e:
        logger.error(f"分析文档失败: {str(e)}", exc_info=True)
        return APIResponse.error(code=500, message="文档分析失败")

