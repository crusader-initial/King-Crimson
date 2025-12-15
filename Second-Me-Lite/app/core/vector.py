from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from typing import List, Dict, Any
import json
import dashscope
from http import HTTPStatus

# 初始化百炼 DashScope SDK
dashscope.api_key = settings.DASHSCOPE_API_KEY

def get_embedding(text: str) -> List[float]:
    """
    生成文本的嵌入向量（使用百炼多模态嵌入模型）
    
    Args:
        text: 要生成向量的文本（注意：限制512 token）
        
    Returns:
        嵌入向量列表（1024 维）
    """
    # 使用百炼 DashScope SDK 调用多模态嵌入模型
    resp = dashscope.MultiModalEmbedding.call(
        model=settings.EMBEDDING_MODEL,
        input=[{'text': text}]
    )
    
    if resp.status_code == HTTPStatus.OK:
        # 从响应中提取向量
        # resp.output 可能是字典或对象，需要兼容处理
        if isinstance(resp.output, dict):
            # 字典格式
            embeddings = resp.output.get('embeddings', [])
            if embeddings and len(embeddings) > 0:
                return embeddings[0].get('embedding', [])
            else:
                raise ValueError("响应中没有找到 embeddings 数据")
        else:
            # 对象格式
            return resp.output.embeddings[0].embedding
    else:
        raise ValueError(f"百炼嵌入模型调用失败: {resp.message} (code: {resp.code})")

def store_embedding(db: Session, chunk_id: int, embedding: List[float]):
    """
    将向量存储到 PostgreSQL 的 chunks 表中
    
    Args:
        db: 数据库会话
        chunk_id: chunk 的 ID
        embedding: 嵌入向量列表
    """
    # 将 list 转换为 PostgreSQL vector 类型可以接受的格式
    # vector 类型可以直接接受数组格式的字符串
    embedding_str = '[' + ','.join(map(str, embedding)) + ']'
    
    # 使用原生 SQL 更新（因为 SQLAlchemy 对 vector 类型的支持可能有限）
    # 使用 CAST 函数避免参数绑定与类型转换语法冲突
    db.execute(
        text("UPDATE chunks SET embedding = CAST(:embedding AS vector) WHERE id = :id"),
        {"embedding": embedding_str, "id": chunk_id}
    )
    db.commit()

def search_similar_chunks(db: Session, query_embedding: List[float], limit: int = 3) -> List[Dict[str, Any]]:
    """
    在 PostgreSQL 中搜索相似的 chunks
    
    Args:
        db: 数据库会话
        query_embedding: 查询文本的嵌入向量
        limit: 返回的结果数量
        
    Returns:
        相似 chunks 的列表，每个包含 id, content, document_id, chunk_index, similarity
    """
    # 将查询向量转换为字符串格式
    query_vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
    
    # 使用余弦相似度搜索（1 - 余弦距离 = 余弦相似度）
    # <=> 是 PGVector 的余弦距离操作符
    # ORDER BY embedding <=> :query 按相似度排序（距离越小越相似）
    query = text("""
        SELECT id, content, document_id, chunk_index, metadata_json,
               1 - (embedding <=> CAST(:query AS vector)) as similarity
        FROM chunks
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:query AS vector)
        LIMIT :limit
    """)
    
    results = db.execute(query, {
        "query": query_vector_str,
        "limit": limit
    })
    
    chunks = []
    for row in results:
        chunks.append({
            "id": row.id,
            "content": row.content,
            "document_id": row.document_id,
            "chunk_index": row.chunk_index,
            "metadata_json": row.metadata_json,
            "similarity": float(row.similarity)
        })
    
    return chunks
