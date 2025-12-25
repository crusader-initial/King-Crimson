from fastapi import APIRouter, Depends, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.services.file_service import FileService
from app.services.document_service import DocumentService
from app.services.chunk_service import DocumentChunker, ChunkService
from app.core.config import Config
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
    role_id: str = Form(...),  # 从 Form 参数获取 role_id
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
    role_id = role_id or metadata_dict.get('role_id')
    
    result = file_service.upload_file(db, file, metadata_dict, role_id)
    return APIResponse.success(
        data=result.get("data", {}),
        message=result.get("message", "文件上传成功")
    )

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

@router.post("/documents/analyze")
def analyze_document(
    db: Session = Depends(get_db)
):
    """
    批量分析所有未分析的文档接口
    
    自动查找状态为 INITIALIZED 或 FAILED 的文档进行分析
    """
    try:
        results = document_service.analyze_all_documents(db)
        return APIResponse.success(
            data=results,
            message=f"文档分析完成：成功 {results['success_count']} 个，失败 {results['failed_count']} 个"
        )
    except Exception as e:
        logger.error(f"批量分析文档失败: {str(e)}", exc_info=True)
        return APIResponse.error(code=500, message="批量分析文档失败")

@router.post("/documents/chunks/process")
def process_all_chunks(
    db: Session = Depends(get_db)
):
    """Process chunks for all documents in batch"""
    try:
        config = Config.from_env()
        chunker = DocumentChunker(
            chunk_size=int(config.get("DOCUMENT_CHUNK_SIZE", 500)),
            overlap=int(config.get("DOCUMENT_CHUNK_OVERLAP", 50)),
        )

        documents = document_service.list_documents(db)
        processed, failed = 0, 0

        chunk_service = ChunkService()
        for doc in documents:
            try:
                if not doc.raw_content:
                    logger.warning(f"Document {doc.id} has no content, skipping...")
                    failed += 1
                    continue

                # Split into chunks and save
                chunks = chunker.split(doc.raw_content)
                for chunk in chunks:
                    chunk.document_id = doc.id
                    chunk_service.save_chunk(chunk)

                processed += 1
                logger.info(
                    f"Document {doc.id} processed: {len(chunks)} chunks created"
                )

            except Exception as e:
                logger.error(f"Failed to process document {doc.id}: {str(e)}")
                failed += 1

        # Commit all changes
        db.commit()

        return APIResponse.success(
            data={
                "total": len(documents),
                "processed": processed,
                "failed": failed,
            },
            message=f"Chunk processing completed: {processed} processed, {failed} failed"
        )

    except Exception as e:
        logger.error(f"Chunk processing failed: {str(e)}", exc_info=True)
        db.rollback()
        return APIResponse.error(
            code=500,
            message=f"Chunk processing failed: {str(e)}"
        )

