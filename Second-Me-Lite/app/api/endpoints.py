from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.chat import chat_with_rag
from app.services.file_service import FileService
from pydantic import BaseModel
import json
from urllib.parse import unquote

router = APIRouter()

# 创建文件服务实例
file_service = FileService()

class ChatRequest(BaseModel):
    query: str

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