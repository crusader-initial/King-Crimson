"""
聊天服务，用于处理不同类型的聊天交互
"""
import logging
from typing import Optional, List, Dict, Any, Type
from sqlalchemy.orm import Session
from openai import OpenAI
from app.core.schemas import ChatRequest
from app.core.config import settings
from app.services.message_builder import MultiTurnMessageBuilder
from app.services.prompt_builder import (
    BasePromptStrategy,
    RoleBasedStrategy,
    SystemPromptStrategy
)

logger = logging.getLogger(__name__)


class ChatService:
    """聊天服务，用于处理不同类型的聊天交互"""
    
    def __init__(self):
        """初始化聊天服务"""
        # 基础策略链，必须包含至少一个基础策略
        self.default_strategy_chain = [BasePromptStrategy, RoleBasedStrategy]
        # 创建自部署模型客户端（使用OpenAI兼容模式）
        self.default_client = OpenAI(
            api_key=settings.CHAT_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )

    def chat(
            self,
            request: ChatRequest,
            db: Optional[Session] = None,
            strategy_chain: Optional[List[Type[SystemPromptStrategy]]] = None,
            json_response: bool = False,
            client: Optional[Any] = None,
            model_params: Optional[Dict[str, Any]] = None,
            context: Optional[Any] = None,
        ) -> Dict[str, Any]:
        """
        主要的聊天方法，返回非流式响应
        
        Args:
            request: 包含消息和其他参数的聊天请求
            db: 数据库会话
            strategy_chain: 可选，要使用的策略类列表
            json_response: 是否请求 LLM 返回 JSON 格式响应
            client: 可选，要使用的 OpenAI 客户端。如果为 None，使用默认客户端
            model_params: 可选，用于覆盖默认值的模型特定参数
            context: 可选，传递给策略的上下文
            
        Returns:
            格式化的响应字典
        """
        logger.info(f"聊天请求: {request}")
        # 构建消息
        message_builder = MultiTurnMessageBuilder(request, strategy_chain=strategy_chain)
        messages = message_builder.build_messages(db, context)
        
        # 记录调试信息
        # logger.info("使用策略链: %s", [s.__name__ for s in strategy_chain] if strategy_chain else "default")
        logger.info("LLM 的最终消息:")
        for msg in messages:
            logger.info(f"角色: {msg['role']}, 内容: {msg['content']}")

        # 使用提供的客户端或默认客户端
        current_client = client or self.default_client
        
        # 调用 LLM API（参考用户数据采集接口的调用方式）
        try:
            response = current_client.chat.completions.create(
                model=settings.CHAT_MODEL,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=False
            )
            # 格式化响应
            return self.format_non_stream_response(response, request)
            
        except Exception as e:
            logger.error(f"聊天失败: {str(e)}", exc_info=True)
            raise

    def format_non_stream_response(self, response: Any, request: ChatRequest) -> Dict[str, Any]:
        """
        将非流式响应格式化为 OpenAI 兼容格式
        
        Args:
            response: LLM 响应对象
            request: 原始聊天请求
            
        Returns:
            格式化后的响应字典
        """
        if hasattr(response, 'choices') and response.choices:
            choice = response.choices[0]
            message = choice.message if hasattr(choice, 'message') else None
            content = message.content if message and hasattr(message, 'content') else ""
            
            return {
                "id": getattr(response, 'id', ''),
                "object": "chat.completion",
                "created": getattr(response, 'created', 0),
                "model": getattr(response, 'model', settings.CHAT_MODEL),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": getattr(choice, 'finish_reason', 'stop')
                }]
            }
        else:
            # 如果响应格式不符合预期，按原样返回
            return response


# 全局聊天服务实例
chat_service = ChatService()
