from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.schemas import ChatRequest, SimpleChatRequest
from app.core.response import APIResponse
from app.services.chat_service import chat_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/chat")
def chat(
    request: SimpleChatRequest,
    load_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """
    聊天接口（非流式响应）
    接受简单的 { query: "..." } 格式，返回 { answer: "..." } 格式
    """
    try:
        # 将简单格式转换为 ChatRequest 格式
        chat_request = ChatRequest(
            messages=[{"role": "user", "content": request.query}],
            temperature=0.7,
            max_tokens=2000,
            stream=False,
            metadata={"load_id": load_id,"role_id" : load_id} 
        )
        
        # 调用聊天服务
        response = chat_service.chat(request=chat_request, db=db)
        
        # 从响应中提取 answer
        answer = ""
        if isinstance(response, dict):
            if "choices" in response and len(response["choices"]) > 0:
                choice = response["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    answer = choice["message"]["content"]
            elif "answer" in response:
                answer = response["answer"]
        
        # 直接返回 { answer: "..." } 格式，以匹配前端期望
        return {"answer": answer}
    except Exception as e:
        logger.error(f"聊天失败: {str(e)}", exc_info=True)
        return APIResponse.error(code=500, message=f"聊天失败: {str(e)}")

