from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from typing import List, Dict, Any
import json
import logging

# 导入 HuggingFace transformers
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)

# 全局变量：模型和 tokenizer（延迟加载）
_model = None
_tokenizer = None
_device = None

def _get_model():
    """
    延迟加载模型，避免启动时加载
    首次调用时会从 HuggingFace 下载模型（需要网络）
    """
    global _model, _tokenizer, _device
    if _model is None or _tokenizer is None:
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

def get_embedding(text: str) -> List[float]:
    """
    生成文本的嵌入向量（使用 BAAI/bge-m3 模型）
    
    Args:
        text: 要生成向量的文本
        
    Returns:
        嵌入向量列表（1024 维）
    """
    model, tokenizer, device = _get_model()
    
    try:
        # 对文本进行编码
        encoded_input = tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=512,  # bge-m3 最大支持 8192，这里设置为 512 以平衡性能和效果
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

def store_embedding(db: Session, chunk_id: int, embedding: List[float]):
    """
    将向量存储到 PostgreSQL 的 chunk 表中
    注意：新表结构中没有 embedding 字段，向量可能存储在其他地方
    这里更新 has_embedding 状态
    
    Args:
        db: 数据库会话
        chunk_id: chunk 的 ID
        embedding: 嵌入向量列表
    """
    # 更新 has_embedding 状态为 true
    # 注意：如果向量存储在其他表，需要单独处理
    db.execute(
        text("UPDATE chunk SET has_embedding = true WHERE id = :id"),
        {"id": chunk_id}
    )
    db.commit()

def search_similar_chunks(db: Session, query_embedding: List[float], limit: int = 3) -> List[Dict[str, Any]]:
    """
    在 PostgreSQL 中搜索相似的 chunks
    注意：新表结构中没有 embedding 字段，此函数可能需要根据实际向量存储位置调整
    
    Args:
        db: 数据库会话
        query_embedding: 查询文本的嵌入向量
        limit: 返回的结果数量
        
    Returns:
        相似 chunks 的列表，每个包含 id, content, document_id, similarity
    """
    # 将查询向量转换为字符串格式
    query_vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
    
    # 注意：如果向量存储在其他表，需要调整查询
    # 这里假设向量可能还在某个地方，或者需要从其他表关联查询
    # 暂时返回空列表，需要根据实际向量存储位置实现
    query = text("""
        SELECT id, content, document_id, tags, topic
        FROM chunk
        WHERE has_embedding = true
        LIMIT :limit
    """)
    
    results = db.execute(query, {
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
            "similarity": 0.0  # 需要根据实际向量计算相似度
        })
    
    return chunks
