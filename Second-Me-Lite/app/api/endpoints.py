from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.chat import chat_with_rag
from app.services.file_service import FileService
from app.services.load_service import LoadService
from app.core.response import APIResponse
from pydantic import BaseModel
from typing import Optional
import json
import logging
from urllib.parse import unquote

router = APIRouter()

logger = logging.getLogger(__name__)

# 创建文件服务实例
file_service = FileService()

class ChatRequest(BaseModel):
    query: str

class CreateLoadRequest(BaseModel):
    """创建用户请求模型"""
    name: str
    email: Optional[str] = ''
    description: Optional[str] = None
    avatar_data: Optional[str] = None
    instance_id: Optional[str] = None
    instance_password: Optional[str] = None
    status: Optional[str] = 'active'

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.post("/chat")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    return chat_with_rag(db, request.query)

@router.post("/file")
def upload_file(
    file: UploadFile = File(...),
    metadata: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    文件上传接口
    """
    # 解析元数据
    metadata_dict = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except:
            pass
    
    return file_service.upload_file(db, file, metadata_dict)

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

@router.post("/loads")
def create_load(
    request: CreateLoadRequest,
    db: Session = Depends(get_db)
):
    """
    创建用户接口
    
    请求体示例:
    {
        "name": "用户名",
        "email": "user@example.com",
        "description": "用户描述",
        "avatar_data": "base64编码的头像数据",
        "instance_id": "实例ID",
        "instance_password": "实例密码",
        "status": "active"
    }
    """
    try:
        load, error, status_code = LoadService.create_load(
            db=db,
            name=request.name,
            email=request.email or '',
            description=request.description,
            avatar_data=request.avatar_data,
            instance_id=request.instance_id,
            instance_password=request.instance_password,
            status=request.status or 'active'
        )
        
        if error:
            return APIResponse.error(code=status_code, message=error)
        
        return APIResponse.success(
            data=load.to_dict(),
            message="用户创建成功"
        )
    except Exception as e:
        logger.error("创建用户失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")

@router.get("/loads/current")
def get_current_load(db: Session = Depends(get_db)):
    """
    获取当前用户记录
    """
    try:
        current_load, error, status_code = LoadService.get_current_load(db)
        
        if error:
            return APIResponse.error(code=status_code, message=error)
        
        # 这里可以根据需要添加 instance_id 相关的逻辑
        # 例如检查实例状态等（参考用户提供的代码）
        load_dict = current_load.to_dict()
        
        # 如果不需要返回敏感信息，可以从字典中移除
        # load_dict.pop('instance_password', None)
        
        return APIResponse.success(
            data=load_dict,
            message="获取成功"
        )
    except Exception as e:
        logger.error("获取当前用户失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")