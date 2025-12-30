"""
聊天服务，用于处理不同类型的聊天交互
"""
import logging
import json
import time
from typing import Optional, List, Dict, Any, Type, Iterator
from sqlalchemy.orm import Session
from openai import OpenAI
from app.core.schemas import ChatRequest
from app.core.config import settings
from app.services.message_builder import MultiTurnMessageBuilder
from app.services.prompt_builder import (
    BasePromptStrategy,
    RoleBasedStrategy,
    KnowledgeEnhancedStrategy,
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
        # 确保 base_url 以 /v1 结尾，与其他服务保持一致
        base_url = settings.OPENAI_BASE_URL.rstrip('/')
        if not base_url.endswith('/v1'):
            base_url = base_url + '/v1'
        
        self.default_client = OpenAI(
            api_key=settings.CHAT_API_KEY,
            base_url=base_url
        )

    def chat(
            self,
            request: ChatRequest,
            db: Optional[Session] = None,
            stream: bool = False,
            strategy_chain: Optional[List[Type[SystemPromptStrategy]]] = None,
            json_response: bool = False,
            client: Optional[Any] = None,
            model_params: Optional[Dict[str, Any]] = None,
            context: Optional[Any] = None,
        ):
        """
        主要的聊天方法，支持流式和非流式响应
        
        Args:
            request: 包含消息和其他参数的聊天请求
            db: 数据库会话
            stream: 是否返回流式响应
            strategy_chain: 可选，要使用的策略类列表
            json_response: 是否请求 LLM 返回 JSON 格式响应
            client: 可选，要使用的 OpenAI 客户端。如果为 None，使用默认客户端
            model_params: 可选，用于覆盖默认值的模型特定参数
            context: 可选，传递给策略的上下文
            
        Returns:
            如果 stream=True，返回 Iterator[str] (Server-Sent Events 格式)
            如果 stream=False，返回 Dict[str, Any] (格式化的响应字典)
        """
        logger.info(f"聊天请求: {request}, stream={stream}")
        # 构建消息
        message_builder = MultiTurnMessageBuilder(request, strategy_chain=strategy_chain)
        messages = message_builder.build_messages(db, context)
        
        # 记录调试信息
        logger.info("LLM 的最终消息:")
        for msg in messages:
            logger.info(f"角色: {msg['role']}, 内容: {msg['content']}")

        # 使用提供的客户端或默认客户端
        current_client = client or self.default_client
        
        # 根据 stream 参数决定返回流式或非流式响应
        if stream:
            # 流式响应
            return self._chat_stream_internal(
                current_client, request, messages
            )
        else:
            # 非流式响应
            try:
                response = current_client.chat.completions.create(
                    model=request.model or settings.CHAT_MODEL,
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

    def _chat_stream_internal(
            self,
            client: Any,
            request: ChatRequest,
            messages: List[Dict[str, Any]]
        ) -> Iterator[str]:
        """
        内部流式响应方法
        
        Args:
            client: OpenAI 客户端
            request: 聊天请求
            messages: 构建好的消息列表
            
        Yields:
            Server-Sent Events 格式的字符串
        """
        # 生成响应 ID 和时间戳
        response_id = f"chatcmpl-{int(time.time())}"
        created = int(time.time())
        
        try:
            # 调用 LLM API（流式模式）
            stream = client.chat.completions.create(
                model=request.model or settings.CHAT_MODEL,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True
            )
            
            # 遍历流式响应
            for chunk in stream:
                # 格式化每个 chunk 为 OpenAI 兼容格式
                chunk_data = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model or settings.CHAT_MODEL,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": None
                    }]
                }
                
                # 提取 chunk 内容
                if hasattr(chunk, 'choices') and chunk.choices:
                    choice = chunk.choices[0]
                    if hasattr(choice, 'delta'):
                        delta = choice.delta
                        if hasattr(delta, 'content') and delta.content:
                            chunk_data["choices"][0]["delta"]["content"] = delta.content
                    # finish_reason 在 choice 对象上，不在 delta 上
                    if hasattr(choice, 'finish_reason') and choice.finish_reason:
                        chunk_data["choices"][0]["finish_reason"] = choice.finish_reason
                        chunk_data["choices"][0]["delta"] = {}  # finish_reason 时 delta 为空
                
                # 转换为 Server-Sent Events 格式
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            
            # 发送结束标记
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"流式聊天失败: {str(e)}", exc_info=True)
            # 发送错误信息
            error_data = {
                "error": {
                    "message": str(e),
                    "type": "server_error"
                }
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

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
