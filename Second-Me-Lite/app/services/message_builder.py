from typing import List, Dict, Any, Type, Optional
from sqlalchemy.orm import Session
from app.core.schemas import ChatRequest
from app.services.prompt_builder import (
    SystemPromptStrategy,
    BasePromptStrategy,
    RoleBasedStrategy,
    KnowledgeEnhancedStrategy,
    SystemPromptBuilder
)


class MessageBuilder:
    """用于构建聊天消息的基类"""
    
    def build_messages(self, db: Optional[Session] = None, context: Optional[Any] = None) -> List[Dict[str, Any]]:
        """构建用于聊天完成的消息"""
        raise NotImplementedError()


class MultiTurnMessageBuilder(MessageBuilder):
    """用于多轮对话的消息构建器"""
    
    def __init__(self, chat_request: ChatRequest, strategy_chain: List[Type[SystemPromptStrategy]] = None):
        """
        使用聊天请求和可选的策略链初始化构建器。
        
        Args:
            chat_request: 用于构建消息的聊天请求
            strategy_chain: 按应用顺序排列的策略类列表。
                          默认为 [BasePromptStrategy, RoleBasedStrategy, KnowledgeEnhancedStrategy]
        """
        self.chat_request = chat_request
        self.strategy_chain = strategy_chain or [BasePromptStrategy, RoleBasedStrategy, KnowledgeEnhancedStrategy]
        
    def build_messages(self, db: Optional[Session] = None, context: Optional[Any] = None) -> List[Dict[str, Any]]:
        """构建用于多轮对话的消息"""

        # 1. 构建系统提示
        builder = SystemPromptBuilder()
        
        # 从下往上构建策略链
        current_strategy = None
        # 从最基础到最高级进行迭代
        for strategy_class in self.strategy_chain:
            if current_strategy is None:
                # BasePromptStrategy
                current_strategy = strategy_class()
            else:
                # 使用临时策略创建新策略
                current_strategy = strategy_class(base_strategy=current_strategy)
        
        if current_strategy is None:
            raise ValueError("No strategy provided")
            
        builder.set_strategy(current_strategy)
        system_prompt = builder.build_prompt(self.chat_request, db, context)
        
        # 2. 构建消息列表：system 消息应该在最前面
        # 过滤掉原有的 system 消息（如果有），避免重复
        other_messages = [
            msg for msg in self.chat_request.messages 
            if msg.get('role') != 'system'
        ]
        
        # 创建新的消息列表，system 消息在最前面
        messages = []
        if system_prompt:  # 只有当 system_prompt 不为空时才添加
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(other_messages)

        return messages
