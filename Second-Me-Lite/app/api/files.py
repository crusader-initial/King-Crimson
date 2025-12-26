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
    """批量处理所有文档的 chunks"""
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
                    logger.warning(f"文档 {doc.id} 没有内容，跳过...")
                    failed += 1
                    continue

                # 分割成 chunks 并保存
                chunks = chunker.split(doc.raw_content)
                for chunk in chunks:
                    chunk.document_id = doc.id
                    chunk_service.save_chunk(chunk)

                processed += 1
                logger.info(
                    f"文档 {doc.id} 处理完成: 创建了 {len(chunks)} 个 chunks"
                )

            except Exception as e:
                logger.error(f"处理文档 {doc.id} 失败: {str(e)}")
                failed += 1

        # 提交所有更改
        db.commit()

        return APIResponse.success(
            data={
                "total": len(documents),
                "processed": processed,
                "failed": failed,
            },
            message=f"Chunk 处理完成: {processed} 个成功，{failed} 个失败"
        )

    except Exception as e:
        logger.error(f"Chunk 处理失败: {str(e)}", exc_info=True)
        db.rollback()
        return APIResponse.error(
            code=500,
            message=f"Chunk 处理失败: {str(e)}"
        )

@router.post("/documents/{document_id}/chunk/embedding")
def process_document_embeddings(
    document_id: int,
    db: Session = Depends(get_db)
):
    """为指定文档的所有 chunks 处理 embeddings"""
    try:
        # 调用服务处理 embeddings
        processed_chunks = document_service.generate_document_chunk_embeddings(
            document_id
        )

        if not processed_chunks:
            logger.warning(f"文档 {document_id} 没有找到 chunks")
            return APIResponse.error(
                message=f"文档 {document_id} 没有找到 chunks"
            )

        return APIResponse.success(
            data={
                "document_id": document_id,
                "total_chunks": len(processed_chunks),
                "processed_chunks": len(
                    [c for c in processed_chunks if c.has_embedding]
                ),
            }
        )

    except Exception as e:
        logger.error(
            f"处理文档 {document_id} 的 embeddings 时出错: {str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"处理文档 {document_id} 的 embeddings 时出错: {str(e)}"
        )

@router.post("/documents/{document_id}/embedding")
def process_document_embedding(
    document_id: int,
    db: Session = Depends(get_db)
):
    """处理文档级别的嵌入向量"""
    try:
        embedding = document_service.process_document_embedding(document_id)
        if embedding is None:
            return APIResponse.error(
                message=f"Failed to process embedding for document {document_id}"
            )

        return APIResponse.success(
            data={"document_id": document_id, "embedding_length": len(embedding)}
        )

    except ValueError as e:
        logger.error(f"Document not found: {str(e)}")
        return APIResponse.error(message=f"Document not found: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing document embedding: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Error processing document embedding: {str(e)}"
        )

