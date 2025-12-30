from typing import Dict, List, Optional, Union, Any
import logging
from openai import OpenAI

from app.core.config import settings
from app.services.L1.bio import Bio, Note, Todo, Chat, UserInfo, get_cur_time
from app.services.L1.prompt import (
    STATUS_BIO_SYSTEM_PROMPT,
    PREFER_LANGUAGE_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class StatusBioGenerator:
    def __init__(self):
        self.preferred_language = "zh_CN"
        self.model_params = {
            "temperature": 0,
            "max_tokens": 1000,
            "top_p": 0.001,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "seed": 42,
        }
        # 直接使用 config.py 中的配置
        self.client = OpenAI(
            api_key=settings.CHAT_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self.model_name = settings.CHAT_MODEL

    def _call_llm_with_retry(self, messages: List[Dict[str, str]], **kwargs) -> Any:
        """调用LLM API
        
        Args:
            messages: API调用的消息列表
            **kwargs: 传递给API调用的其他参数
            
        Returns:
            语言模型的API响应对象
            
        Raises:
            Exception: 如果API调用失败
        """
        try:
            return self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                **self.model_params,
                **kwargs
            )
        except Exception as e:
            logger.error(f"API调用失败: {str(e)}")
            raise

    def _build_message(self, user_info: UserInfo, language: str) -> List[Dict[str, str]]:
        """构建用于生成状态传记的消息列表

        Args:
            user_info: 用户信息对象
            language: 首选语言

        Returns:
            格式化的LLM API消息列表
        """
        messages = [
            {"role": "system", "content": STATUS_BIO_SYSTEM_PROMPT},
            {"role": "user", "content": str(user_info)},
        ]

        if language:
            messages.append(
                {
                    "role": "system",
                    "content": PREFER_LANGUAGE_SYSTEM_PROMPT.format(language=language),
                }
            )

        return messages


    def generate_status_bio(self, notes: List[Note], todos: List[Todo], 
                           chats: List[Chat]) -> Bio:
        """基于用户的笔记、待办事项和聊天记录生成状态传记

        Args:
            notes: 用户的笔记列表
            todos: 用户的待办事项列表
            chats: 用户的聊天记录列表

        Returns:
            包含生成内容的Bio对象
        """
        cur_time = get_cur_time()

        user_info = UserInfo(cur_time, notes, todos, chats)
        messages = self._build_message(user_info, self.preferred_language)

        answer = self._call_llm_with_retry(messages)
        content = answer.choices[0].message.content
        logger.info(f"Generated content: {content}")

        # 创建并返回Bio对象，确保所有内容字段都有值
        return Bio(
            contentThirdView=content,  # 将生成的内容放入third_view
            content=content,  # 将生成的内容放入second_view
            summaryThirdView=content,  # 将生成的内容放入third_view
            summary=content,  # 将生成的内容放入second_view
            attributeList=[],
            shadesList=[],
        )
