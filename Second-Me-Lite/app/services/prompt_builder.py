"""
系统提示词构建器及相关策略
"""
from typing import Optional, Any
import logging
from sqlalchemy.orm import Session

from app.core.schemas import ChatRequest
from app.services.L1 import default_l1_retriever
from app.services.knowledge_service import default_retriever
from app.services.role_service import RoleService

# 系统提示词模板
JUDGE_PROMPT = """你是{user_name}的Me.bot，作为{user_name}的管家和助手，帮助{user_name}与专家进行对接。
具体来说，你的任务是评估专家的回复是否满足{user_name}的需求，基于{user_name}的要求和专家的回复。如果需求未得到满足，你应该根据你对{user_name}的理解，代表{user_name}提供反馈和补充信息。如果需求已满足，你应该礼貌地回应。"""

CONTEXT_PROMPT = """你是{user_name}的Me.bot，作为{user_name}的管家和助手，帮助{user_name}与专家进行对接。
具体来说，你的任务是判断是否可以添加更多关于{user_name}的详细信息，以帮助专家更好地完成任务，基于{user_name}的要求。
如果可以进一步补充，请提供额外的信息；否则，直接传达{user_name}的要求。"""

MEMORY_PROMPT = """你是{user_name}的"第二自我"，这是由{user_name}创建的个性化AI。
你可以根据你对{user_name}的背景信息和过往记录的理解，帮助{user_name}回答问题。"""


logger = logging.getLogger(__name__)


class SystemPromptStrategy:
    """系统提示词构建策略的基类"""
    def build_prompt(self, request: ChatRequest, db: Optional[Session] = None, context: Optional[Any] = None) -> str:
        """构建系统提示词"""
        raise NotImplementedError()


class BasePromptStrategy(SystemPromptStrategy):
    """最基础的系统提示词构建策略"""
    def build_prompt(self, request: ChatRequest, db: Optional[Session] = None, context: Optional[Any] = None) -> str:
        """返回基础的系统提示词"""
        # 尝试在消息中查找系统消息
        if request.messages:
            for message in request.messages:
                if message.get('role') == 'system':
                    return message.get('content', '')
        
        # 如果未找到系统消息，返回默认空提示词
        return ""

class RoleBasedStrategy(SystemPromptStrategy):
    """基于角色的系统提示词构建策略"""
    def __init__(self, base_strategy: SystemPromptStrategy):
        self.base_strategy = base_strategy

    def build_prompt(self, request: ChatRequest, db: Optional[Session] = None, context: Optional[Any] = None) -> str:
        """基于角色构建系统提示词"""
        # 如果可用，从元数据中获取 role_id
        role_id = None
        if hasattr(request, 'metadata') and request.metadata:
            role_id = request.metadata.get('role_id')
        
        if role_id and db:
            role, error, status = RoleService.get_role_by_id(db, role_id)
            if role and status == 200:
                prompt = role.system_prompt
                logger.info(f"RoleBasedStrategy (from role): {prompt}")
                return prompt
            elif error:
                logger.warning(f"获取角色失败: {error} (status: {status})")
                
        prompt = self.base_strategy.build_prompt(request, db, context)
        # logger.info(f"RoleBasedStrategy (from base): {prompt}")
        return prompt


class KnowledgeEnhancedStrategy(SystemPromptStrategy):
    """知识增强的系统提示词构建策略"""
    def __init__(self, base_strategy: SystemPromptStrategy):
        self.base_strategy = base_strategy

    def get_user_message(self, request: ChatRequest) -> str:
        """
        从消息字段中获取最后一条用户消息。
        """
        if request.messages:
            # 查找最后一条 role='user' 的消息
            for message in reversed(request.messages):
                if message.get('role') == 'user':
                    return message.get('content', '')
        
        return ''

    def build_prompt(self, request: ChatRequest, db: Optional[Session] = None, context: Optional[Any] = None) -> str:
        """构建知识增强的系统提示词"""
        base_prompt = self.base_strategy.build_prompt(request, db, context)
        
        logger.info(f"KnowledgeEnhancedStrategy request: {request}")
        logger.info(f"KnowledgeEnhancedStrategy (from base): {base_prompt}")
        
        # 如果启用，添加知识检索结果
        knowledge_sections = []
        user_message = self.get_user_message(request)
        
        # 从元数据中获取 role_id
        role_id = None
        if hasattr(request, 'metadata') and request.metadata:
            role_id = request.metadata.get('role_id')
        
        # 如果角色存在，从角色表读取配置并执行检索
        if role_id and db:
            role, error, status = RoleService.get_role_by_id(db, role_id)
            if role and status == 200:
                # L0 检索
                if role.enable_l0_retrieval:
                    l0_knowledge = default_retriever.retrieve(user_message)
                    if l0_knowledge:
                        knowledge_sections.append(f"参考知识:\n{l0_knowledge}")
                
                # L1 检索
                if role.enable_l1_retrieval:
                    l1_knowledge = default_l1_retriever.retrieve(user_message, role_id=role_id)
                    if l1_knowledge:
                        knowledge_sections.append(f"参考维度:\n{l1_knowledge}")
            
        if knowledge_sections:
            if len(base_prompt) == 0:
                prompt = "\n\n".join(knowledge_sections)
            else:
                prompt = base_prompt + "\n\n" + "\n\n".join(knowledge_sections)
            logger.info(f"KnowledgeEnhancedStrategy (with knowledge): {prompt}")
            return prompt
            
        return base_prompt


class SystemPromptBuilder:
    """系统提示词构建器"""
    def __init__(self):
        self.strategy: Optional[SystemPromptStrategy] = None

    def set_strategy(self, strategy: SystemPromptStrategy):
        self.strategy = strategy

    def build_prompt(self, request: ChatRequest, db: Optional[Session] = None, context: Optional[Any] = None) -> str:
        if not self.strategy:
            raise ValueError("No strategy set for SystemPromptBuilder")
        prompt = self.strategy.build_prompt(request, db, context)
        # logger.info(f"Final system prompt: {prompt}")
        return prompt
