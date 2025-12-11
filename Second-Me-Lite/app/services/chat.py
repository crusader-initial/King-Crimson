from sqlalchemy.orm import Session
from app.models.document import ChatHistory
from app.core.vector import get_collection
from app.core.config import settings
from openai import OpenAI

client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL
)

def chat_with_rag(db: Session, query: str):
    # 1. Retrieve context
    collection = get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=3
    )
    
    context_texts = results['documents'][0] if results['documents'] else []
    context_str = "\n\n".join(context_texts)
    
    # 2. Build Prompt
    system_prompt = f"""You are a helpful assistant. Use the following context to answer the user's question.
    
    Context:
    {context_str}
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]
    
    # 3. Call LLM
    response = client.chat.completions.create(
        model=settings.CHAT_MODEL,
        messages=messages,
        temperature=0.7
    )
    
    answer = response.choices[0].message.content
    
    # 4. Save History
    user_msg = ChatHistory(role="user", content=query)
    ai_msg = ChatHistory(role="assistant", content=answer)
    db.add(user_msg)
    db.add(ai_msg)
    db.commit()
    
    return {"answer": answer, "context": context_texts}
