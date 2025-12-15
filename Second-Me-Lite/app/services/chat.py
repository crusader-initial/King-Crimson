from sqlalchemy.orm import Session
from app.models.document import ChatHistory
from app.core.vector import get_embedding, search_similar_chunks
from app.core.config import settings
from openai import OpenAI
from typing import Dict, List

client = OpenAI(
    api_key=settings.DASHSCOPE_API_KEY,
    base_url=settings.OPENAI_BASE_URL
)

def chat_with_rag(db: Session, query: str) -> Dict:
    """
    基于 RAG（检索增强生成）的对话函数
    
    Args:
        db: 数据库会话
        query: 用户查询
        
    Returns:
        包含 answer 和 context 的字典
    """
    # 1. 生成查询向量并检索相似的 chunks（使用 PostgreSQL + PGVector）
    query_embedding = get_embedding(query)
    similar_chunks = search_similar_chunks(db, query_embedding, limit=3)
    
    # 提取上下文文本
    context_texts = [chunk["content"] for chunk in similar_chunks]
    context_str = "\n\n".join(context_texts)
    
    # 2. 构建 Prompt
    system_prompt = f"""You are a helpful assistant. Use the following context to answer the user's question.
    
    Context:
    {context_str}
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]
    
    # 3. 调用 LLM
    response = client.chat.completions.create(
        model=settings.CHAT_MODEL,
        messages=messages,
        temperature=0.7
    )
    
    answer = response.choices[0].message.content
    
    # 4. 保存历史记录
    user_msg = ChatHistory(role="user", content=query)
    ai_msg = ChatHistory(role="assistant", content=answer)
    db.add(user_msg)
    db.add(ai_msg)
    db.commit()
    
    return {"answer": answer, "context": context_texts}
