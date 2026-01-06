from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from typing import List, Dict, Any, Optional
import json
import logging
import numpy as np
from openai import OpenAI

# 导入 HuggingFace transformers (延迟导入)
# from transformers import AutoTokenizer, AutoModel
# import torch
# import torch.nn.functional as F

logger = logging.getLogger(__name__)

# 全局变量：模型和 tokenizer（延迟加载）
_model = None
_tokenizer = None
_device = None
_openai_client = None

def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        api_key = settings.EMBEDDING_API_KEY or settings.CHAT_API_KEY
        base_url = settings.EMBEDDING_BASE_URL or settings.OPENAI_BASE_URL
        
        if not api_key:
            raise ValueError("API Key is missing. Please set CHAT_API_KEY or EMBEDDING_API_KEY in .env")
            
        _openai_client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
    return _openai_client

def _get_model():
    """
    延迟加载模型，避免启动时加载
    如果使用 OpenAI Embedding，则不需要加载本地模型
    """
    if settings.EMBEDDING_PROVIDER == "openai":
        return None, None, None

    global _model, _tokenizer, _device
    if _model is None or _tokenizer is None:
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
        except ImportError:
            logger.error("Required libraries 'torch' and 'transformers' are not installed. "
                         "Please install them to use local embeddings, or switch to 'openai' provider.")
            raise

        model_name = settings.EMBEDDING_MODEL
        logger.info(f"Loading embedding model: {model_name}")
        
        try:
            _tokenizer = AutoTokenizer.from_pretrained(model_name)
            _model = AutoModel.from_pretrained(model_name)
            _model.eval()  # 设置为评估模式
            
            # 检测设备（GPU 或 CPU）
            _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            _model = _model.to(_device)
            
            logger.info(f"Embedding model loaded successfully on {_device}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}", exc_info=True)
            raise
    
    return _model, _tokenizer, _device

def get_embedding(text: str, max_length: int = 512) -> List[float]:
    """
    生成文本的嵌入向量
    支持 local (BAAI/bge-m3) 和 openai 模式
    """
    if settings.EMBEDDING_PROVIDER == "openai":
        try:
            client = _get_openai_client()
            kwargs = {
                "model": settings.OPENAI_EMBEDDING_MODEL,
                "input": text
            }
            # 只有部分 OpenAI 模型支持 dimensions 参数，且 bge-m3 通过 API 调用时通常不需要传 dimensions
            # 如果是 text-embedding-3 系列才传
            if "text-embedding-3" in settings.OPENAI_EMBEDDING_MODEL:
                kwargs["dimensions"] = settings.OPENAI_EMBEDDING_DIMENSIONS
                
            response = client.embeddings.create(**kwargs)
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate openai embedding: {str(e)}", exc_info=True)
            raise

    # Local mode
    model, tokenizer, device = _get_model()
    
    try:
        import torch
        import torch.nn.functional as F
        # 对文本进行编码
        encoded_input = tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors='pt'
        )
        
        # 将输入移到设备（GPU 或 CPU）
        encoded_input = {k: v.to(device) for k, v in encoded_input.items()}
        
        # 生成嵌入向量
        with torch.no_grad():
            model_output = model(**encoded_input)
            # bge-m3 使用 CLS token 的表示
            embeddings = model_output.last_hidden_state[:, 0, :]  # 取 CLS token
            # 归一化（bge-m3 通常需要归一化以获得更好的相似度计算）
            embeddings = F.normalize(embeddings, p=2, dim=1)
        
        # 转换为列表并移到 CPU
        embedding = embeddings[0].cpu().numpy().tolist()
        
        return embedding
    except Exception as e:
        logger.error(f"Failed to generate embedding: {str(e)}", exc_info=True)
        raise

def get_embedding_with_chunking(text: str, max_text_length: int = 8192, chunk_size: int = 512) -> List[float]:
    """
    生成文本的嵌入向量，如果文本过长则分块处理后求平均（使用 BAAI/bge-m3 模型）
    参考逻辑：如果文本超过 max_text_length，则分块处理，然后对分块的 embeddings 求平均
    
    Args:
        text: 要生成向量的文本
        max_text_length: 最大文本长度（字符数），超过此长度会分块处理
        chunk_size: 每个分块的最大 token 长度
        
    Returns:
        嵌入向量列表（1024 维）
    """
    # 如果文本长度不超过限制，直接处理
    if len(text) <= max_text_length:
        return get_embedding(text, max_length=chunk_size)
    
    # 文本过长，需要分块处理
    logger.info(f"Text length {len(text)} exceeds max_text_length {max_text_length}, splitting into chunks")
    
    # 将文本分割成多个块
    chunks = []
    chunk_texts = []
    
    for i in range(0, len(text), max_text_length):
        chunk_text = text[i:i + max_text_length]
        chunk_texts.append(chunk_text)
    
    logger.info(f"Split text into {len(chunk_texts)} chunks")
    
    # 批量生成每个块的 embeddings
    try:
        embeddings_array = get_embeddings_batch(chunk_texts, max_length=chunk_size)
        
        # 如果只有一个块，直接返回
        if len(chunk_texts) == 1:
            return embeddings_array[0].tolist()
        
        # 多个块，求平均
        avg_embedding = np.mean(embeddings_array, axis=0)
        return avg_embedding.tolist()
        
    except Exception as e:
        logger.error(f"Error generating embedding with chunking: {str(e)}", exc_info=True)
        raise

def get_embeddings_batch(texts: List[str], max_length: int = 512) -> np.ndarray:
    """
    批量生成文本的嵌入向量
    支持 local (BAAI/bge-m3) 和 openai 模式
    """
    if settings.EMBEDDING_PROVIDER == "openai":
        try:
            client = _get_openai_client()
            kwargs = {
                "model": settings.OPENAI_EMBEDDING_MODEL,
                "input": texts
            }
            if "text-embedding-3" in settings.OPENAI_EMBEDDING_MODEL:
                kwargs["dimensions"] = settings.OPENAI_EMBEDDING_DIMENSIONS
                
            response = client.embeddings.create(**kwargs)
            # 保证顺序一致
            embeddings = [data.embedding for data in response.data]
            return np.array(embeddings)
        except Exception as e:
            logger.error(f"Failed to generate openai embeddings batch: {str(e)}", exc_info=True)
            raise

    # Local mode
    model, tokenizer, device = _get_model()
    
    try:
        import torch
        import torch.nn.functional as F
        # 批量编码文本
        encoded_input = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors='pt'
        )
        
        # 将输入移到设备（GPU 或 CPU）
        encoded_input = {k: v.to(device) for k, v in encoded_input.items()}
        
        # 批量生成嵌入向量
        with torch.no_grad():
            model_output = model(**encoded_input)
            # bge-m3 使用 CLS token 的表示
            embeddings = model_output.last_hidden_state[:, 0, :]  # 取 CLS token
            # 归一化
            embeddings = F.normalize(embeddings, p=2, dim=1)
        
        # 转换为 numpy array 并移到 CPU
        embeddings_np = embeddings.cpu().numpy()
        
        return embeddings_np
    except Exception as e:
        logger.error(f"Failed to generate embeddings batch: {str(e)}", exc_info=True)
        raise

def store_embedding(db: Session, chunk_id: int, embedding: List[float]):
    """
    将单个 chunk 的向量存储到 PostgreSQL 的 chunk_embedding 表中（使用 pgvector）
    同时更新 chunk 表的 has_embedding 状态
    
    Args:
        db: 数据库会话
        chunk_id: chunk 的 ID
        embedding: 嵌入向量列表（1024 维）
    """
    try:
        # 将向量转换为 PostgreSQL 的 vector 类型格式
        embedding_str = '[' + ','.join(map(str, embedding)) + ']'
        
        # 使用 UPSERT 操作存储向量到 chunk_embedding 表
        # 使用 CAST 函数进行类型转换，避免 SQLAlchemy 参数占位符与 PostgreSQL 类型转换语法冲突
        query = text("""
            INSERT INTO chunk_embedding (chunk_id, embedding, create_time, update_time)
            VALUES (:chunk_id, CAST(:embedding AS vector), NOW(), NOW())
            ON CONFLICT (chunk_id) 
            DO UPDATE SET 
                embedding = EXCLUDED.embedding,
                update_time = NOW()
        """)
        
        db.execute(query, {
            "chunk_id": chunk_id,
            "embedding": embedding_str
        })
        
        # 更新 chunk 表的 has_embedding 状态
        db.execute(
            text("UPDATE chunk SET has_embedding = true WHERE id = :id"),
            {"id": chunk_id}
        )
        
        db.commit()
        logger.debug(f"Stored chunk embedding for chunk {chunk_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error storing chunk embedding: {str(e)}", exc_info=True)
        raise

def store_embeddings_batch(db: Session, chunk_ids: List[int], embeddings: np.ndarray):
    """
    批量存储 chunks 的向量到 PostgreSQL 的 chunk_embedding 表中（使用 pgvector）
    同时批量更新 chunk 表的 has_embedding 状态
    
    Args:
        db: 数据库会话
        chunk_ids: chunk ID 列表
        embeddings: numpy array，形状为 (len(chunk_ids), embedding_dim)
    """
    if not chunk_ids or len(chunk_ids) == 0:
        return
    
    if embeddings is None or len(embeddings) == 0:
        logger.warning("No embeddings provided for batch storage")
        return
    
    if len(chunk_ids) != len(embeddings):
        raise ValueError(f"chunk_ids length ({len(chunk_ids)}) does not match embeddings length ({len(embeddings)})")
    
    try:
        # 批量插入/更新向量到 chunk_embedding 表
        # 使用 CAST 函数进行类型转换，避免 SQLAlchemy 参数占位符与 PostgreSQL 类型转换语法冲突
        for chunk_id, embedding in zip(chunk_ids, embeddings):
            embedding_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
            embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'
            
            query = text("""
                INSERT INTO chunk_embedding (chunk_id, embedding, create_time, update_time)
                VALUES (:chunk_id, CAST(:embedding AS vector), NOW(), NOW())
                ON CONFLICT (chunk_id) 
                DO UPDATE SET 
                    embedding = EXCLUDED.embedding,
                    update_time = NOW()
            """)
            
            db.execute(query, {
                "chunk_id": chunk_id,
                "embedding": embedding_str
            })
        
        # 批量更新 chunk 表的 has_embedding 状态
        db.execute(
            text("UPDATE chunk SET has_embedding = true WHERE id = ANY(:ids)"),
            {"ids": chunk_ids}
        )
        
        db.commit()
        logger.info(f"Successfully stored {len(chunk_ids)} chunk embeddings to pgvector")
    except Exception as e:
        db.rollback()
        logger.error(f"Error storing chunk embeddings batch: {str(e)}", exc_info=True)
        raise

def store_document_embedding(db: Session, document_id: int, embedding: List[float]):
    """
    将文档级别的向量存储到 PostgreSQL 的 document_embedding 表中（使用 pgvector）
    
    Args:
        db: 数据库会话
        document_id: 文档的 ID
        embedding: 嵌入向量列表（1024 维）
    """
    try:
        # 将向量转换为 PostgreSQL 的 vector 类型格式
        # pgvector 使用 '[' + ','.join(map(str, embedding)) + ']' 格式
        embedding_str = '[' + ','.join(map(str, embedding)) + ']'
        
        # 使用 UPSERT 操作（如果存在则更新，不存在则插入）
        # 使用 CAST 函数进行类型转换，避免 SQLAlchemy 参数占位符与 PostgreSQL 类型转换语法冲突
        query = text("""
            INSERT INTO document_embedding (document_id, embedding, create_time, update_time)
            VALUES (:document_id, CAST(:embedding AS vector), NOW(), NOW())
            ON CONFLICT (document_id) 
            DO UPDATE SET 
                embedding = EXCLUDED.embedding,
                update_time = NOW()
        """)
        
        db.execute(query, {
            "document_id": document_id,
            "embedding": embedding_str
        })
        db.commit()
        logger.debug(f"Stored document embedding for document {document_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error storing document embedding: {str(e)}", exc_info=True)
        raise

def get_chunk_embedding(db: Session, chunk_id: int) -> Optional[List[float]]:
    """
    从 PostgreSQL 获取 chunk 级别的向量
    
    Args:
        db: 数据库会话
        chunk_id: chunk 的 ID
        
    Returns:
        嵌入向量列表，如果不存在则返回 None
    """
    try:
        query = text("""
            SELECT embedding::text
            FROM chunk_embedding
            WHERE chunk_id = :chunk_id
        """)
        
        result = db.execute(query, {"chunk_id": chunk_id}).first()
        
        if result and result[0]:
            # 将 PostgreSQL vector 类型的字符串表示转换为列表
            # 格式通常是 '[1.0,2.0,3.0,...]'
            embedding_str = result[0].strip('[]')
            embedding = [float(x) for x in embedding_str.split(',')]
            return embedding
        
        return None
    except Exception as e:
        logger.error(f"Error getting chunk embedding: {str(e)}", exc_info=True)
        return None

def get_document_embedding(db: Session, document_id: int) -> Optional[List[float]]:
    """
    从 PostgreSQL 获取文档级别的向量
    
    Args:
        db: 数据库会话
        document_id: 文档的 ID
        
    Returns:
        嵌入向量列表，如果不存在则返回 None
    """
    try:
        query = text("""
            SELECT embedding::text
            FROM document_embedding
            WHERE document_id = :document_id
        """)
        
        result = db.execute(query, {"document_id": document_id}).first()
        
        if result and result[0]:
            # 将 PostgreSQL vector 类型的字符串表示转换为列表
            # 格式通常是 '[1.0,2.0,3.0,...]'
            embedding_str = result[0].strip('[]')
            embedding = [float(x) for x in embedding_str.split(',')]
            return embedding
        
        return None
    except Exception as e:
        logger.error(f"Error getting document embedding: {str(e)}", exc_info=True)
        return None

def search_similar_chunks(db: Session, query_embedding: List[float], limit: int = 3) -> List[Dict[str, Any]]:
    """
    在 PostgreSQL 中使用 pgvector 搜索相似的 chunks
    
    Args:
        db: 数据库会话
        query_embedding: 查询文本的嵌入向量
        limit: 返回的结果数量
        
    Returns:
        相似 chunks 的列表，每个包含 id, content, document_id, tags, topic, similarity
    """
    try:
        # 将查询向量转换为 PostgreSQL 的 vector 类型格式
        query_vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        # 使用 pgvector 的余弦距离操作符 <=> 进行相似度搜索
        # 注意：<=> 返回的是余弦距离（0-2），需要转换为相似度（1-(-1)）
        # 余弦相似度 = 1 - 余弦距离
        # 由于 bge-m3 模型已经归一化，余弦距离范围是 0-2，相似度范围是 1-(-1)
        query = text("""
            SELECT 
                c.id, 
                c.content, 
                c.document_id, 
                c.tags, 
                c.topic,
                1 - (ce.embedding <=> CAST(:query_vector AS vector)) as similarity
            FROM chunk c
            INNER JOIN chunk_embedding ce ON c.id = ce.chunk_id
            WHERE c.has_embedding = true
            ORDER BY ce.embedding <=> CAST(:query_vector AS vector)
            LIMIT :limit
        """)
        
        results = db.execute(query, {
            "query_vector": query_vector_str,
            "limit": limit
        })
        
        chunks = []
        for row in results:
            chunks.append({
                "id": row.id,
                "content": row.content,
                "document_id": row.document_id,
                "tags": row.tags,
                "topic": row.topic,
                "similarity": float(row.similarity) if row.similarity is not None else 0.0
            })
        
        logger.debug(f"Found {len(chunks)} similar chunks for query")
        return chunks
        
    except Exception as e:
        logger.error(f"Error searching similar chunks: {str(e)}", exc_info=True)
        return []
