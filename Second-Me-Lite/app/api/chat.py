from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.schemas import ChatRequest
from app.core.response import APIResponse
from app.services.chat_service import chat_service
from app.services.prompt_builder import (
    BasePromptStrategy,
    RoleBasedStrategy,
    KnowledgeEnhancedStrategy
)
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/chat")
def chat(
    body: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    聊天接口 - 流式响应（兼容 OpenAI API 格式）

    请求参数：兼容 OpenAI Chat Completions API 格式
    - messages: List[Dict[str, str]]，标准的 OpenAI 消息列表，格式：
        [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, who are you?"},
            {"role": "assistant", "content": "I am a helpful assistant."},
            {"role": "user", "content": "What can you do for me?"}  
        ]
    - metadata: Dict[str, Any]，请求处理的额外参数（必需）：
        {
            "role_id": "uuid-string",     // 必需，用于系统定制的角色 UUID
            "enable_l0_retrieval": true,   // 是否启用知识检索（可选）
            "enable_l1_retrieval": false   // 是否启用高级知识检索（可选）
        }
    - stream: bool，是否流式响应（默认: True）
    - model: str，模型标识符（可选，默认使用配置的模型）
    - temperature: float，控制随机性（默认: 0.1）
    - max_tokens: int，最大生成 token 数（默认: 2000）

    响应：标准 OpenAI Chat Completions API 格式
    当 stream=true 时（Server-Sent Events）：
    - id: str，响应唯一标识符
    - object: "chat.completion.chunk"
    - created: int，时间戳
    - model: str，模型标识符
    - system_fingerprint: str，系统指纹
    - choices: [
        {
          "index": 0,
          "delta": {"content": str},
          "finish_reason": null 或 "stop"
        }
      ]
    
    最后一个事件将是: data: [DONE]
    
    当 stream=false 时：
    - 包含完整消息内容的完整响应对象
    """
    try:
        # 验证 role_id 是必需字段
        metadata = body.metadata or {}
        if not metadata.get("role_id"):
            raise HTTPException(
                status_code=400,
                detail="role_id is required in metadata"
            )
        
        # 使用 chat_service 处理请求，使用 OpenAI 兼容格式
        response = chat_service.chat(
            request=body,
            db=db,
            stream=body.stream,  # 遵循请求中的 stream 参数
            json_response=False,
            strategy_chain=[BasePromptStrategy, RoleBasedStrategy, KnowledgeEnhancedStrategy]
        )
        
        # 根据流式或非流式响应进行相应处理
        if body.stream:
            # 流式响应，返回 Server-Sent Events 响应
            return StreamingResponse(
                response,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # 非流式响应，返回完整的 JSON 响应
            return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天失败: {str(e)}", exc_info=True)
        return APIResponse.error(code=500, message=f"聊天失败: {str(e)}")

