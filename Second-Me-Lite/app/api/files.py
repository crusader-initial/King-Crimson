from fastapi import APIRouter, Depends, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.core.database import get_db, SessionLocal
from app.services.file_service import FileService
from app.services.document_service import DocumentService
from app.core.response import APIResponse
from app.core.schemas import ExportMessagesToDocumentRequest
from app.core.utils import serialize_value
from app.services.L1.l1_manager import generate_l1_from_l0, store_l1_data, generate_and_store_status_bio
from app.models.document import Document
from app.models.role import Role
import json
import logging
import threading
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
        documents = document_service.list_documents(db)
        processed, failed = 0, 0
        failed_docs = []

        for doc in documents:
            try:
                # 使用服务层方法处理单个文档的分块
                chunks_count = document_service.process_document_chunks(db, doc.id)
                processed += 1
                logger.info(
                    f"文档 {doc.id} 处理完成: 创建了 {chunks_count} 个 chunks"
                )
            except ValueError as e:
                # 文档不存在或没有内容的情况
                logger.warning(f"文档 {doc.id} 跳过: {str(e)}")
                failed += 1
                failed_docs.append({"id": doc.id, "name": doc.name, "error": str(e)})
            except Exception as e:
                logger.error(f"处理文档 {doc.id} 失败: {str(e)}")
                failed += 1
                failed_docs.append({"id": doc.id, "name": doc.name, "error": str(e)})

        return APIResponse.success(
            data={
                "total": len(documents),
                "processed": processed,
                "failed": failed,
                "failed_documents": failed_docs,
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

def _process_export_messages_background(
    load_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None
):
    """
    后台任务：处理消息导出为文档的完整流程
    
    在新线程中执行，包含所有处理步骤：
    1. 将聊天记录消息转换为文档并落表
    2. 文件内容分析
    3. 文档内容分块
    4. 文档分块向量化
    5. 文档向量化
    6. 身份传记数据生成
    7. L1层数据生成
    """
    # 在新线程中创建新的数据库会话
    db = SessionLocal()
    try:
        logger.info(f"[后台任务] 步骤1: 开始导出消息为文档 (load_id={load_id})")
        result = file_service.export_messages_to_document(
            db=db,
            load_id=load_id,
            title=title,
            description=description
        )
        
        if not result.get("data") or not result.get("data", {}).get("documents"):
            logger.info(f"[后台任务] 导出成功，但没有创建文档 (load_id={load_id})")
            return
        
        documents = result.get("data", {}).get("documents", [])
        logger.info(f"[后台任务] 步骤1完成: 成功创建 {len(documents)} 个文档")
        
        # 获取 role_id（从第一个文档关联的角色获取，或从 load_id 查询）
        role_id = None
        if documents:
            # 从第一个文档获取 role_id
            first_doc_id = documents[0].get("document_id")
            if first_doc_id:
                first_doc = db.query(Document).filter(Document.id == first_doc_id).first()
                if first_doc and first_doc.role_id:
                    role_id = first_doc.role_id
                    logger.info(f"[后台任务] 从文档获取到 role_id: {role_id}")
        
        # 如果还没有 role_id，尝试从 load_id 查询
        if not role_id:
            # 将 load_id 转换为字符串（数据库 load_id 是 varchar 类型）
            load_id_str = str(load_id) if not isinstance(load_id, str) else load_id
            role = db.query(Role).filter(Role.load_id == load_id_str).first()
            if role:
                role_id = role.id
                logger.info(f"[后台任务] 从 load_id 查询到 role_id: {role_id}")
        
        # 对每个文档执行步骤2-5
        processed_docs = []
        failed_docs = []
        
        for doc_info in documents:
            document_id = doc_info.get("document_id")
            if not document_id:
                logger.warning(f"[后台任务] 文档信息缺少 document_id: {doc_info}")
                failed_docs.append({"document_id": None, "error": "缺少 document_id"})
                continue
            
            try:
                logger.info(f"[后台任务] 开始处理文档 {document_id}")
                
                # 获取文档对象
                document = db.query(Document).filter(Document.id == document_id).first()
                if not document:
                    logger.error(f"[后台任务] 文档 {document_id} 不存在")
                    failed_docs.append({"document_id": document_id, "error": "文档不存在"})
                    continue
                
                # 第二步：文件内容分析
                logger.info(f"[后台任务] 步骤2: 开始分析文档 {document_id}")
                try:
                    document_service.analyze_document(db, document)
                    logger.info(f"[后台任务] 步骤2完成: 文档 {document_id} 分析成功")
                except Exception as e:
                    logger.error(f"[后台任务] 步骤2失败: 文档 {document_id} 分析失败: {str(e)}")
                    failed_docs.append({"document_id": document_id, "step": 2, "error": str(e)})
                    continue
                
                # 第三步：文档内容分块
                logger.info(f"[后台任务] 步骤3: 开始分块文档 {document_id}")
                try:
                    chunks_count = document_service.process_document_chunks(db, document_id)
                    logger.info(f"[后台任务] 步骤3完成: 文档 {document_id} 分块成功，创建了 {chunks_count} 个 chunks")
                except Exception as e:
                    logger.error(f"[后台任务] 步骤3失败: 文档 {document_id} 分块失败: {str(e)}")
                    failed_docs.append({"document_id": document_id, "step": 3, "error": str(e)})
                    continue
                
                # 第四步：文档分块向量化
                logger.info(f"[后台任务] 步骤4: 开始为文档 {document_id} 的 chunks 生成向量")
                try:
                    processed_chunks = document_service.generate_document_chunk_embeddings(document_id)
                    if processed_chunks:
                        logger.info(f"[后台任务] 步骤4完成: 文档 {document_id} 的 {len(processed_chunks)} 个 chunks 向量化成功")
                    else:
                        logger.warning(f"[后台任务] 步骤4: 文档 {document_id} 没有找到 chunks")
                except Exception as e:
                    logger.error(f"[后台任务] 步骤4失败: 文档 {document_id} 的 chunks 向量化失败: {str(e)}")
                    failed_docs.append({"document_id": document_id, "step": 4, "error": str(e)})
                    continue
                
                # 第五步：文档向量化
                logger.info(f"[后台任务] 步骤5: 开始为文档 {document_id} 生成文档级向量")
                try:
                    embedding = document_service.process_document_embedding(document_id)
                    if embedding:
                        logger.info(f"[后台任务] 步骤5完成: 文档 {document_id} 向量化成功，向量维度: {len(embedding)}")
                    else:
                        logger.warning(f"[后台任务] 步骤5: 文档 {document_id} 向量化返回 None")
                except Exception as e:
                    logger.error(f"[后台任务] 步骤5失败: 文档 {document_id} 向量化失败: {str(e)}")
                    failed_docs.append({"document_id": document_id, "step": 5, "error": str(e)})
                    continue
                
                processed_docs.append({
                    "document_id": document_id,
                    "filename": doc_info.get("filename"),
                    "participant_name": doc_info.get("participant_name")
                })
                logger.info(f"[后台任务] 文档 {document_id} 处理完成")
                
            except Exception as e:
                logger.error(f"[后台任务] 处理文档 {document_id} 时发生错误: {str(e)}", exc_info=True)
                failed_docs.append({"document_id": document_id, "error": str(e)})
                continue
        
        # 第六步：身份传记数据生成（只需要执行一次，使用 role_id）
        if role_id:
            logger.info(f"[后台任务] 步骤6: 开始生成身份传记数据 (role_id={role_id})")
            try:
                status_bio = generate_and_store_status_bio(role_id=role_id)
                if status_bio:
                    logger.info(f"[后台任务] 步骤6完成: 身份传记数据生成成功")
                else:
                    logger.warning(f"[后台任务] 步骤6: 身份传记数据生成返回 None")
            except Exception as e:
                logger.error(f"[后台任务] 步骤6失败: 身份传记数据生成失败: {str(e)}", exc_info=True)
        else:
            logger.warning("[后台任务] 步骤6跳过: 未找到 role_id")
        
        # 第七步：L1层数据生成（只需要执行一次，使用 role_id）
        if role_id:
            logger.info(f"[后台任务] 步骤7: 开始生成L1层数据 (role_id={role_id})")
            try:
                l1_generation_result = generate_l1_from_l0(role_id=role_id)
                if l1_generation_result:
                    version_number = store_l1_data(db, l1_generation_result, role_id=role_id)
                    logger.info(f"[后台任务] 步骤7完成: L1层数据生成成功，版本: {version_number}")
                else:
                    logger.warning(f"[后台任务] 步骤7: L1层数据生成返回 None")
            except Exception as e:
                logger.error(f"[后台任务] 步骤7失败: L1层数据生成失败: {str(e)}", exc_info=True)
        else:
            logger.warning("[后台任务] 步骤7跳过: 未找到 role_id")
        
        logger.info(f"[后台任务] 导出任务完成: 创建 {len(documents)} 个文档，成功处理 {len(processed_docs)} 个，失败 {len(failed_docs)} 个")
        
    except Exception as e:
        logger.error(f"[后台任务] 导出消息为文档失败: {str(e)}", exc_info=True)
    finally:
        db.close()


@router.post("/file/export-messages")
def export_messages_to_document(
    request: ExportMessagesToDocumentRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    将消息导出为文档并执行完整的处理流程（异步执行）
    
    接口会立即返回，告知任务已开始执行。实际的处理流程会在后台线程中异步执行。
    
    根据 load_id 获取用户参与的所有单聊会话，为每个会话创建单独的文档，然后依次执行：
    1. 将聊天记录消息转换为文档并落表
    2. 文件内容分析
    3. 文档内容分块
    4. 文档分块向量化
    5. 文档向量化
    6. 身份传记数据生成
    7. L1层数据生成
    
    请求体示例:
    {
        "load_id": "user-uuid",  // 必填
        "title": "聊天记录导出",  // 可选（用于文档标题前缀）
        "description": "从消息导出的文档"  // 可选
    }
    
    响应:
    {
        "code": 200,
        "message": "任务已开始执行",
        "data": {
            "load_id": "user-uuid",
            "status": "processing"
        }
    }
    """
    try:
        # 验证参数
        if not request.load_id:
            return APIResponse.error(code=400, message="load_id 必须提供")
        
        # 启动后台线程执行任务
        thread = threading.Thread(
            target=_process_export_messages_background,
            args=(request.load_id, request.title, request.description),
            daemon=True  # 设置为守护线程，主进程退出时自动结束
        )
        thread.start()
        
        logger.info(f"已启动后台任务处理消息导出 (load_id={request.load_id})")
        
        # 立即返回响应，告知任务已开始
        return APIResponse.success(
            data={
                "load_id": request.load_id,
                "status": "processing",
                "message": "任务已开始在后台执行"
            },
            message="任务已开始执行，处理结果请查看日志"
        )
        
    except Exception as e:
        logger.error(f"启动导出消息任务失败: {str(e)}", exc_info=True)
        # 如果是 HTTPException，提取状态码和详情
        if hasattr(e, 'status_code') and hasattr(e, 'detail'):
            return APIResponse.error(code=e.status_code, message=str(e.detail))
        return APIResponse.error(code=500, message=f"启动导出消息任务失败: {str(e)}")

