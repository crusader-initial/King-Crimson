from fastapi import APIRouter, Depends, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.core.database import get_db
from app.services.file_service import FileService
from app.services.document_service import DocumentService
from app.services.chunk_service import DocumentChunker, ChunkService
from app.core.config import Config
from app.core.response import APIResponse
from app.core.schemas import ExportMessagesToDocumentRequest
from app.models.conversation import Conversation, Message
from app.models.role import Role
from app.models.load import Load
from io import BytesIO
from datetime import datetime
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

@router.post("/file/export-messages")
def export_messages_to_document(
    request: ExportMessagesToDocumentRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    将消息导出为文档并上传
    
    根据 load_id 或 role_id 获取所有相关的消息，组合成文档后走上传逻辑
    
    请求体示例:
    {
        "load_id": "user-uuid",  // 或
        "role_id": "role-uuid",  // 与 load_id 二选一
        "title": "聊天记录导出",  // 可选
        "description": "从消息导出的文档"  // 可选
    }
    """
    try:
        # 1. 验证参数
        if not request.load_id and not request.role_id:
            return APIResponse.error(code=400, message="load_id 或 role_id 必须提供其中一个")
        
        if request.load_id and request.role_id:
            return APIResponse.error(code=400, message="load_id 和 role_id 只能提供其中一个")
        
        # 2. 确定 role_id（用于文档上传）
        role_id = None
        conversations = []
        
        if request.load_id:
            # 根据 load_id 获取所有会话
            load = db.query(Load).filter(Load.id == request.load_id).first()
            if not load:
                return APIResponse.error(code=404, message=f"未找到用户 ID: {request.load_id}")
            
            # 获取该用户的所有会话
            conversations = db.query(Conversation).filter(
                Conversation.user_id == request.load_id
            ).all()
            
            # 尝试获取该用户对应的角色（通过 Role.uuid = loads.id）
            role = db.query(Role).filter(Role.uuid == request.load_id).first()
            if role:
                role_id = role.id
            else:
                # 如果没有找到角色，尝试从会话中获取第一个角色的 role_id
                if conversations:
                    # 从会话中获取 participant_id（通常是 role_id）
                    role_id = conversations[0].participant_id
                else:
                    return APIResponse.error(code=404, message=f"用户 {request.load_id} 没有找到相关的会话或角色")
        
        elif request.role_id:
            # 根据 role_id 获取所有会话
            role = db.query(Role).filter(Role.id == request.role_id).first()
            if not role:
                return APIResponse.error(code=404, message=f"未找到角色 ID: {request.role_id}")
            
            role_id = request.role_id
            
            # 获取该角色相关的所有会话（作为 participant_id）
            conversations = db.query(Conversation).filter(
                Conversation.participant_id == request.role_id,
                Conversation.participant_type == 'role'
            ).all()
        
        if not conversations:
            return APIResponse.error(code=404, message="未找到相关的会话")
        
        # 3. 获取所有会话的消息
        conversation_ids = [conv.id for conv in conversations]
        
        messages = db.query(Message).filter(
            Message.conversation_id.in_(conversation_ids)
        ).order_by(Message.created_at.asc()).all()
        
        if not messages:
            return APIResponse.error(code=404, message="未找到相关的消息")
        
        # 4. 格式化消息为文档内容
        document_content = format_messages_to_document(messages, conversations, db)
        
        # 5. 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = request.title if request.title else f"聊天记录_{timestamp}.txt"
        # 确保文件名以 .txt 结尾
        if not filename.endswith('.txt'):
            filename = f"{filename}.txt"
        
        # 6. 创建临时文件对象
        file_content = document_content.encode('utf-8')
        file_obj = BytesIO(file_content)
        file_obj.name = filename
        
        # 创建 UploadFile 对象
        upload_file = UploadFile(
            file=file_obj,
            filename=filename
        )
        
        # 7. 准备元数据
        metadata = {
            'title': request.title if request.title else f"聊天记录导出_{timestamp}",
            'description': request.description if request.description else "从消息导出的文档"
        }
        
        # 8. 调用现有的文档上传逻辑
        result = file_service.upload_file(db, upload_file, metadata, role_id)
        
        return APIResponse.success(
            data=result.get("data", {}),
            message=result.get("message", "消息导出为文档成功")
        )
        
    except Exception as e:
        logger.error(f"导出消息为文档失败: {str(e)}", exc_info=True)
        return APIResponse.error(code=500, message=f"导出消息为文档失败: {str(e)}")


def format_messages_to_document(messages: list, conversations: list, db: Session) -> str:
    """
    将消息列表格式化为文档内容
    
    Args:
        messages: 消息列表
        conversations: 会话列表
        db: 数据库会话
        
    Returns:
        格式化后的文档内容（字符串）
    """
    # 创建会话ID到会话标题的映射
    conv_dict = {conv.id: conv.title or f"会话_{conv.id[:8]}" for conv in conversations}
    
    # 创建角色ID到角色名的映射
    role_dict = {}
    load_dict = {}
    
    # 获取所有相关的角色和用户信息
    role_ids = set()
    load_ids = set()
    
    for msg in messages:
        role_ids.add(msg.sender_id)
        role_ids.add(msg.receiver_id)
        load_ids.add(msg.sender_id)
        load_ids.add(msg.receiver_id)
    
    # 查询角色信息
    roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
    for role in roles:
        role_dict[role.id] = role.name
    
    # 查询用户信息
    loads = db.query(Load).filter(Load.id.in_(load_ids)).all()
    for load in loads:
        load_dict[load.id] = load.name
    
    # 按会话分组消息
    messages_by_conv = {}
    for msg in messages:
        if msg.conversation_id not in messages_by_conv:
            messages_by_conv[msg.conversation_id] = []
        messages_by_conv[msg.conversation_id].append(msg)
    
    # 构建文档内容
    lines = []
    lines.append("=" * 80)
    lines.append("聊天记录导出")
    lines.append("=" * 80)
    lines.append(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"会话数量: {len(conversations)}")
    lines.append(f"消息总数: {len(messages)}")
    lines.append("")
    
    # 按会话输出消息
    for conv_id, conv_messages in messages_by_conv.items():
        conv_title = conv_dict.get(conv_id, f"会话_{conv_id[:8]}")
        lines.append("")
        lines.append("-" * 80)
        lines.append(f"会话: {conv_title}")
        lines.append("-" * 80)
        lines.append("")
        
        for msg in conv_messages:
            # 确定发送者名称
            sender_name = role_dict.get(msg.sender_id) or load_dict.get(msg.sender_id) or "未知用户"
            
            # 格式化时间
            time_str = msg.created_at.strftime('%Y-%m-%d %H:%M:%S') if msg.created_at else "未知时间"
            
            # 输出消息
            lines.append(f"[{time_str}] {sender_name}:")
            lines.append(msg.content)
            lines.append("")
    
    return "\n".join(lines)

