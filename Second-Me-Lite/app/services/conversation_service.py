from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from typing import Tuple, Optional, List
from datetime import datetime
import logging
from app.models.conversation import Conversation, Message

logger = logging.getLogger(__name__)


class ConversationService:
    """会话服务类，处理会话相关的业务逻辑"""
    
    @staticmethod
    def get_or_create_conversation(
        db: Session,
        user_id: str,
        participant_id: str,
        participant_type: str,
        title: Optional[str] = None
    ) -> Tuple[Optional[Conversation], Optional[str], int]:
        """
        获取或创建会话（支持双向查询）
        如果会话存在（无论谁发起），返回现有会话；不存在则创建新会话
        
        Args:
            db: 数据库会话
            user_id: 用户ID（loads.id）
            participant_id: 参与者ID（roles.id 或其他用户ID）
            participant_type: 参与者类型（必传，如 'role'）
            title: 会话标题（可选）
            
        Returns:
            Tuple[Conversation对象, 错误消息, HTTP状态码]
            成功: (Conversation对象, None, 200)
            失败: (None, 错误消息, 状态码)
        """
        try:
            # 验证必填字段
            if not user_id or not user_id.strip():
                return None, "用户ID不能为空", 400
            if not participant_id or not participant_id.strip():
                return None, "参与者ID不能为空", 400
            
            user_id = user_id.strip()
            participant_id = participant_id.strip()
            participant_type = participant_type.strip()
            
            # 双向查询：检查两种组合
            # 1. user_id = A, participant_id = B
            # 2. user_id = B, participant_id = A
            existing_conversation = db.query(Conversation).filter(
                or_(
                    (Conversation.user_id == user_id) & (Conversation.participant_id == participant_id),
                    (Conversation.user_id == participant_id) & (Conversation.participant_id == user_id)
                ),
                Conversation.participant_type == participant_type
            ).first()
            
            if existing_conversation:
                logger.info(f"找到已存在会话: {existing_conversation.id} - user_id: {user_id}, participant_id: {participant_id}")
                return existing_conversation, None, 200
            
            # 创建新会话（总是以传入的user_id为主）
            new_conversation = Conversation(
                user_id=user_id,
                participant_id=participant_id,
                participant_type=participant_type,
                title=title.strip() if title else None,
                unread_count=0,
                is_pinned=False,
                is_muted=False
            )
            
            db.add(new_conversation)
            db.commit()
            db.refresh(new_conversation)
            
            logger.info(f"成功创建新会话: {new_conversation.id} - user_id: {user_id}, participant_id: {participant_id}")
            return new_conversation, None, 200
            
        except IntegrityError as e:
            db.rollback()
            # 如果是因为唯一约束冲突，尝试再次查询
            if "uq_conversation_participants" in str(e):
                existing_conversation = db.query(Conversation).filter(
                    or_(
                        (Conversation.user_id == user_id) & (Conversation.participant_id == participant_id),
                        (Conversation.user_id == participant_id) & (Conversation.participant_id == user_id)
                    ),
                    Conversation.participant_type == participant_type
                ).first()
                if existing_conversation:
                    return existing_conversation, None, 200
            logger.error(f"数据库完整性错误: {str(e)}", exc_info=True)
            return None, "创建会话失败：数据完整性错误", 400
        except Exception as e:
            db.rollback()
            logger.error(f"获取或创建会话失败: {str(e)}", exc_info=True)
            return None, f"获取或创建会话失败: {str(e)}", 500
    
    @staticmethod
    def get_conversation_by_id(
        db: Session,
        conversation_id: str
    ) -> Tuple[Optional[Conversation], Optional[str], int]:
        """
        根据ID获取会话
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            
        Returns:
            Tuple[Conversation对象, 错误消息, HTTP状态码]
        """
        try:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                return None, f"未找到ID为 {conversation_id} 的会话", 404
            
            return conversation, None, 200
            
        except Exception as e:
            logger.error(f"获取会话失败: {str(e)}", exc_info=True)
            return None, f"获取会话失败: {str(e)}", 500
    
    @staticmethod
    def get_conversation_between_participants(
        db: Session,
        participant1_id: str,
        participant2_id: str,
        participant_type: str = 'role'
    ) -> Tuple[Optional[Conversation], Optional[str], int]:
        """
        获取两个参与者之间的会话（无论谁发起）
        
        Args:
            db: 数据库会话
            participant1_id: 参与者1的ID
            participant2_id: 参与者2的ID
            participant_type: 参与者类型（默认 'role'）
            
        Returns:
            Tuple[Conversation对象, 错误消息, HTTP状态码]
        """
        try:
            conversation = db.query(Conversation).filter(
                or_(
                    (Conversation.user_id == participant1_id) & (Conversation.participant_id == participant2_id),
                    (Conversation.user_id == participant2_id) & (Conversation.participant_id == participant1_id)
                ),
                Conversation.participant_type == participant_type
            ).first()
            
            if not conversation:
                return None, f"未找到参与者之间的会话", 404
            
            return conversation, None, 200
            
        except Exception as e:
            logger.error(f"获取会话失败: {str(e)}", exc_info=True)
            return None, f"获取会话失败: {str(e)}", 500
    
    @staticmethod
    def get_conversations_by_user_id(
        db: Session,
        user_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> Tuple[List[Conversation], Optional[str], int]:
        """
        根据用户ID获取所有会话列表
        
        Args:
            db: 数据库会话
            user_id: 用户ID（loads.id）
            limit: 限制返回数量（可选）
            offset: 偏移量（默认0）
            
        Returns:
            Tuple[会话列表, 错误消息, HTTP状态码]
        """
        try:
            query = db.query(Conversation).filter(
                Conversation.user_id == user_id
            ).order_by(
                Conversation.last_message_at.desc().nulls_last(),
                Conversation.created_at.desc()
            )
            
            if limit:
                query = query.limit(limit).offset(offset)
            
            conversations = query.all()
            return conversations, None, 200
            
        except Exception as e:
            logger.error(f"获取用户会话列表失败: {str(e)}", exc_info=True)
            return [], f"获取用户会话列表失败: {str(e)}", 500
    
    @staticmethod
    def update_conversation(
        db: Session,
        conversation_id: str,
        title: Optional[str] = None,
        is_pinned: Optional[bool] = None,
        is_muted: Optional[bool] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        更新会话信息
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            title: 会话标题（可选）
            is_pinned: 是否置顶（可选）
            is_muted: 是否静音（可选）
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                return False, f"未找到ID为 {conversation_id} 的会话"
            
            if title is not None:
                conversation.title = title.strip() if title else None
            if is_pinned is not None:
                conversation.is_pinned = is_pinned
            if is_muted is not None:
                conversation.is_muted = is_muted
            
            conversation.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"成功更新会话 {conversation_id}")
            return True, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"更新会话失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def update_last_message(
        db: Session,
        conversation_id: str,
        last_message_content: str
    ) -> Tuple[bool, Optional[str]]:
        """
        更新会话的最后一条消息信息
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            last_message_content: 最后一条消息内容
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                return False, f"未找到ID为 {conversation_id} 的会话"
            
            conversation.last_message_at = datetime.utcnow()
            conversation.last_message_content = last_message_content
            conversation.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"成功更新会话 {conversation_id} 的最后一条消息")
            return True, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"更新会话最后消息失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def increment_unread_count(
        db: Session,
        conversation_id: str,
        increment: int = 1
    ) -> Tuple[bool, Optional[str]]:
        """
        增加会话的未读消息数
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            increment: 增加的数量（默认1）
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                return False, f"未找到ID为 {conversation_id} 的会话"
            
            conversation.unread_count = (conversation.unread_count or 0) + increment
            conversation.updated_at = datetime.utcnow()
            
            db.commit()
            return True, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"增加未读消息数失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def reset_unread_count(
        db: Session,
        conversation_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        重置会话的未读消息数为0
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                return False, f"未找到ID为 {conversation_id} 的会话"
            
            conversation.unread_count = 0
            conversation.updated_at = datetime.utcnow()
            
            db.commit()
            return True, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"重置未读消息数失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def delete_conversation(
        db: Session,
        conversation_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        删除会话（级联删除相关消息）
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                return False, f"未找到ID为 {conversation_id} 的会话"
            
            db.delete(conversation)
            db.commit()
            
            logger.info(f"成功删除会话 {conversation_id}")
            return True, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"删除会话失败: {str(e)}", exc_info=True)
            return False, str(e)

