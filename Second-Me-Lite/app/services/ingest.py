from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.models.document import Document, Chunk
from app.core.vector import get_embedding, store_embedding
import json
from typing import Dict

def process_upload(db: Session, file: UploadFile) -> Dict:
    """
    处理上传的文件：切片、生成向量并存储到 PostgreSQL
    
    Args:
        db: 数据库会话
        file: 上传的文件
        
    Returns:
        包含 document_id 和 chunks_count 的字典
    """
    # 1. 读取文件内容
    content = file.file.read().decode("utf-8")  # 假设是文本/markdown 文件
    
    # 2. 创建 Document 记录
    doc = Document(filename=file.filename, content=content)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # 3. 文本切片（简单的字符分割）
    chunk_size = 500
    overlap = 50
    chunks = []
    chunk_texts = []  # 用于批量生成向量
    
    start = 0
    text_len = len(content)
    chunk_index = 0
    
    while start < text_len:
        end = start + chunk_size
        chunk_text = content[start:end]
        
        # 准备元数据
        metadata = {
            "filename": file.filename,
            "document_id": doc.id,
            "chunk_index": chunk_index
        }
        
        # 保存到数据库（先不存储向量）
        db_chunk = Chunk(
            document_id=doc.id,
            content=chunk_text,
            chunk_index=chunk_index,
            metadata_json=metadata  # JSONB 类型可以直接接受字典
        )
        db.add(db_chunk)
        db.flush()  # 获取 chunk.id，但不提交
        chunks.append(db_chunk)
        chunk_texts.append(chunk_text)
        
        start += (chunk_size - overlap)
        chunk_index += 1
    
    db.commit()  # 提交所有 chunks，获取它们的 ID
    
    # 4. 生成向量并存储到 PostgreSQL（而不是 ChromaDB）
    chunk_ids = [chunk.id for chunk in chunks]
    embeddings = []
    
    # 批量生成向量
    for chunk_text in chunk_texts:
        embedding = get_embedding(chunk_text)
        embeddings.append(embedding)
    
    # 存储向量到 PostgreSQL
    for chunk_id, embedding in zip(chunk_ids, embeddings):
        store_embedding(db, chunk_id, embedding)
    
    return {"document_id": doc.id, "chunks_count": len(chunks)}
