from pathlib import Path
import os
import logging
import json
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
from app.models.document import Document, Memory, Chunk
from app.core.vector import get_embedding, store_embedding
from app.core.config import settings
from app.services.processors import ProcessorFactory, UnsupportedFileType

logger = logging.getLogger(__name__)

# 允许的文件格式
ALLOWED_EXTENSIONS = {"txt", "pdf", "md"}


def allowed_file(filename: str) -> bool:
    """检查文件格式是否允许"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


class FileService:
    """文件服务，处理文件上传和删除的业务逻辑"""
    
    def __init__(self):
        # 获取文件存储目录配置
        raw_content_dir = getattr(settings, "RAW_CONTENT_DIR", "resources/raw_content")
        base_dir = getattr(settings, "BASE_DIR", ".")
        
        logger.info(f"初始化文件服务, base_dir: {base_dir}")
        logger.info(f"文件存储目录配置: {raw_content_dir}")
        
        # 如果路径不是绝对路径，基于 base_dir 构建完整路径
        if not os.path.isabs(raw_content_dir):
            raw_content_dir = os.path.join(base_dir, raw_content_dir)
            logger.info(f"构建完整路径: {raw_content_dir}")
        
        # 转换为 Path 对象并确保目录存在
        self.base_path = Path(raw_content_dir).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"存储路径已创建: {self.base_path}")
    
    def upload_file(
        self, 
        db: Session, 
        file: UploadFile, 
        metadata: Optional[Dict[str, Any]] = None,
        role_id: Optional[str] = None  # 角色ID（字符串格式，需要转换为 Integer）
    ) -> Dict[str, Any]:
        """
        上传文件并处理
        """
        logger.info("开始处理文件上传请求")

        if not role_id:
            logger.warning("role_id 为空")
            raise HTTPException(status_code=400, detail="role_id 是必需的")
        # 1. 文件验证和读取（合并检查文件名、格式验证和内容读取）
        try:
            # 检查文件名
            if not file.filename:
                logger.warning("文件名为空")
                raise HTTPException(status_code=400, detail="未选择文件")
            
            filename = file.filename
            logger.info(f"收到文件: {filename}")
            
            # 验证文件格式
            if not allowed_file(filename):
                logger.warning(f"不支持的文件格式: {filename}")
                allowed_extensions = ", ".join(ALLOWED_EXTENSIONS)
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的文件格式。仅允许以下格式: {allowed_extensions}"
                )
            
            # 读取文件内容到内存（获取文件大小，但不保存到磁盘）
            file_content = file.file.read()
            filesize = len(file_content)
            logger.info(f"文件读取完成: {filename}, 大小: {filesize} 字节")
            
            # 重置文件指针，以便后续使用
            file.file.seek(0)
        except Exception as e:
            logger.error(f"文件验证或读取失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")
        
        # 2. 先检查文件是否已存在（通过 memories 表检查，需同时匹配文件名、大小和 role_id）
        existing_memory = db.query(Memory).filter(
            Memory.name == filename,
            Memory.size == filesize,
            Memory.role_id == role_id,  
            Memory.status == 'active'
        ).first()
        if existing_memory:
            logger.warning(f"文件已存在: {filename}, role_id: {role_id}")
            raise HTTPException(
                status_code=409,
                detail=f"文件 '{filename}' 已存在"
            )
        
        # 3. 文件不存在，保存文件到磁盘
        try:
            filepath = self._save_file_to_disk(filename, file_content)
            logger.info(f"文件已保存到磁盘: {filepath}")
        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")

        # 4. 使用 ProcessorFactory 自动检测并处理文件
        try:
            doc_result = ProcessorFactory.auto_detect_and_process(str(filepath))
            logger.info(f"文件处理成功: {filename}, 类型: {doc_result.file_type}")
        except UnsupportedFileType as e:
            logger.warning(f"不支持的文件类型: {filename}, 错误: {str(e)}")
            # 删除已保存的文件
            if os.path.exists(filepath):
                os.remove(filepath)
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {str(e)}"
            )
        
        # 5. 创建 Document 和 Memory 记录（先创建 Document，再创建 Memory，放在同一个事务中）
        try:
            # 先创建 Document 记录
            document = Document(
                name=filename,
                title=metadata.get('title', filename) if metadata else filename,
                mime_type=doc_result.mime_type,
                raw_content=doc_result.raw_content,
                user_description=metadata.get('description', '上传的文档') if metadata else '',
                url=str(filepath),
                document_size=doc_result.file_size,
                extract_status='SUCCESS',
                embedding_status='INITIALIZED',
                analyze_status='INITIALIZED',
                role_id=role_id if role_id else None  # 关联角色ID（varchar(36)类型）
            )
            db.add(document)
            db.flush()  # 刷新以获取 document.id，但不提交事务
            
            # 再创建 Memory 记录（使用 document.id）
            memory = Memory(
                role_id=role_id,
                name=filename,
                size=filesize,
                type=self._get_file_type(filename),
                path=str(filepath),
                meta_data=json.dumps(metadata, ensure_ascii=False) if metadata else None,
                document_id=document.id,
                status='active'
            )
            db.add(memory)
            
            # 提交事务
            db.commit()
            logger.info(f"Document 记录创建成功: {document.id}")
            logger.info(f"Memory 记录创建成功: {memory.id}")
            
            # 返回成功结果
            return {
                "success": True,
                "message": "文件上传成功",
                "data": {
                    "memory_id": memory.id,
                    "document_id": document.id,
                    "filename": filename,
                    "file_path": str(filepath),
                    "file_size": filesize,
                    "meta_data": metadata if metadata else None
                }
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"创建 Document 或 Memory 记录失败: {str(e)}", exc_info=True)
            # 删除已保存的文件
            if os.path.exists(filepath):
                os.remove(filepath)
            raise HTTPException(status_code=500, detail=f"创建记录失败: {str(e)}")
        #
        # # 7. 处理文档（切片、生成向量）
        # try:
        #     chunks_count = self._process_document(db, document, doc_result.raw_content)
        #     logger.info("文件上传处理完成")
        #
        #     return {
        #         "success": True,
        #         "message": "上传成功",
        #         "data": {
        #             "memory_id": memory.id,
        #             "document_id": document.id,
        #             "filename": filename,
        #             "file_path": str(filepath),
        #             "file_size": filesize,
        #             "chunks_count": chunks_count
        #         }
        #     }
        # except Exception as e:
        #     logger.error(f"文档处理失败: {str(e)}", exc_info=True)
        #     # 即使处理失败，文件已保存，返回基本信息
        #     return {
        #         "success": True,
        #         "message": "文件已上传，但处理失败",
        #         "data": {
        #             "memory_id": memory.id,
        #             "document_id": document.id,
        #             "filename": filename,
        #             "file_path": str(filepath),
        #             "file_size": filesize,
        #             "error": str(e)
        #         }
        #     }
    
    def delete_file(self, db: Session, filename: str) -> Dict[str, Any]:
        """
        删除文件
        
        Args:
            db: 数据库会话
            filename: 文件名
            
        Returns:
            包含删除结果的字典
            
        Raises:
            HTTPException: 各种错误情况
        """
        logger.info(f"开始处理文件删除请求: {filename}")
        
        try:
            # 1. 查找 Memory 记录
            memory = db.query(Memory).filter(
                Memory.name == filename,
                Memory.status == 'active'
            ).first()
            
            if not memory:
                logger.warning(f"文件记录未找到: {filename}")
                raise HTTPException(
                    status_code=404,
                    detail=f"文件 '{filename}' 不存在"
                )
            
            file_path = memory.path
            document_id = memory.document_id
            
            # 2. 删除相关的 chunks
            if document_id:
                chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
                for chunk in chunks:
                    db.delete(chunk)
                logger.info(f"已删除 {len(chunks)} 个 chunks")
                
                # 3. 删除 Document 记录
                document = db.query(Document).filter(Document.id == document_id).first()
                if document:
                    db.delete(document)
                    logger.info(f"已删除 Document 记录: {document_id}")
            
            # 4. 更新 Memory 状态为 deleted（软删除）
            memory.status = 'deleted'
            memory.document_id = None
            db.commit()
            logger.info(f"已更新 Memory 状态为 deleted: {memory.id}")
            
            # 5. 删除物理文件
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"已删除物理文件: {file_path}")
            
            return {
                "success": True,
                "message": f"文件 '{filename}' 已成功删除"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"删除文件时发生错误: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")
    
    def _process_document(self, db: Session, document: Document, content: str) -> int:
        """
        处理文档：切片、生成向量
        
        Args:
            db: 数据库会话
            document: 文档对象
            content: 文档内容
            
        Returns:
            切片数量
        """
        # 文本切片
        chunk_size = 500
        overlap = 50
        chunks = []
        chunk_texts = []
        
        start = 0
        text_len = len(content)
        
        while start < text_len:
            end = start + chunk_size
            chunk_text = content[start:end]
            
            db_chunk = Chunk(
                document_id=document.id,
                content=chunk_text,
                has_embedding=False
            )
            db.add(db_chunk)
            db.flush()
            chunks.append(db_chunk)
            chunk_texts.append(chunk_text)
            
            start += (chunk_size - overlap)
        
        db.commit()
        
        # 生成向量并存储
        for chunk, chunk_text in zip(chunks, chunk_texts):
            try:
                embedding = get_embedding(chunk_text)
                store_embedding(db, chunk.id, embedding)
            except Exception as e:
                logger.warning(f"生成向量失败 (chunk {chunk.id}): {str(e)}")
        
        # 更新文档的 embedding_status
        document.embedding_status = 'SUCCESS'
        db.commit()
        
        return len(chunks)
    
    def _get_file_type(self, filename: str) -> str:
        """获取文件类型（用于 Memory 表）"""
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        type_map = {
            'txt': 'text',
            'md': 'markdown',
            'pdf': 'pdf'
        }
        return type_map.get(ext, 'unknown')
    
    def _save_file_to_disk(self, filename: str, file_content: bytes) -> Path:
        """保存文件到磁盘
        
        Args:
            filename: 文件名
            file_content: 文件内容（字节）
            
        Returns:
            文件路径
        """
        try:
            # 确保目录存在
            self.base_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"确保存储目录存在: {self.base_path}")
            
            # 生成文件路径
            filepath = self.base_path / filename
            logger.info(f"准备保存文件到: {filepath}")
            
            # 保存文件
            with open(filepath, 'wb') as f:
                f.write(file_content)
            
            filesize = os.path.getsize(filepath)
            logger.info(f"文件保存成功: {filepath}, 大小: {filesize} 字节")
            
            return filepath
            
        except Exception as e:
            logger.error(f"保存文件到磁盘失败: {str(e)}", exc_info=True)
            raise

