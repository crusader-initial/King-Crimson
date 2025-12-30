from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Tuple, Optional, List
from datetime import datetime
import logging
from app.models.conversation import Message, Conversation
from app.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)


class MessageService:
    """消息服务类，处理消息相关的业务逻辑"""
    
    @staticmethod
    def create_message(
        db: Session,
        conversation_id: str,
        sender_id: str,
        receiver_id: str,
        content: str,
        message_type: str = 'text',
        attachment_url: Optional[str] = None
    ) -> Tuple[Optional[Message], Optional[str], int]:
        """
        创建新消息
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            sender_id: 发送者ID（user_id 或 role_id）
            receiver_id: 接收者ID（user_id 或 role_id）
            content: 消息内容
            message_type: 消息类型（默认 'text'）
            attachment_url: 附件URL（可选）
            
        Returns:
            Tuple[Message对象, 错误消息, HTTP状态码]
            成功: (Message对象, None, 200)
            失败: (None, 错误消息, 状态码)
        """
        try:
            # 验证必填字段
            if not conversation_id or not conversation_id.strip():
                return None, "会话ID不能为空", 400
            if not sender_id or not sender_id.strip():
                return None, "发送者ID不能为空", 400
            if not receiver_id or not receiver_id.strip():
                return None, "接收者ID不能为空", 400
            if not content or not content.strip():
                return None, "消息内容不能为空", 400
            
            # 验证消息类型
            valid_types = ['text', 'image', 'file', 'audio', 'video']
            if message_type not in valid_types:
                return None, f"无效的消息类型: {message_type}。允许的类型: {', '.join(valid_types)}", 400
            
            # 验证会话是否存在
            conversation, error, status = ConversationService.get_conversation_by_id(
                db=db,
                conversation_id=conversation_id
            )
            if error:
                return None, f"会话不存在: {error}", status
            
            # 创建新消息
            new_message = Message(
                conversation_id=conversation_id.strip(),
                sender_id=sender_id.strip(),
                receiver_id=receiver_id.strip(),
                content=content.strip(),
                message_type=message_type.strip(),
                attachment_url=attachment_url.strip() if attachment_url else None,
                is_sent=True,
                is_delivered=False,
                is_read=False
            )
            
            db.add(new_message)
            
            # 更新会话的最后一条消息信息
            ConversationService.update_last_message(
                db=db,
                conversation_id=conversation_id,
                last_message_content=content.strip()
            )
            
            # 如果接收者是用户，增加未读消息数
            # 注意：这里需要根据业务逻辑判断，如果接收者是用户，则增加未读数
            # 假设 receiver_id 是 user_id 时，需要增加未读数
            # 但这里需要根据实际业务逻辑调整
            # 暂时不自动增加，由前端或业务逻辑控制
            
            db.commit()
            db.refresh(new_message)
            
            logger.info(f"成功创建消息: {new_message.id} - conversation_id: {conversation_id}")
            return new_message, None, 200
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"数据库完整性错误: {str(e)}", exc_info=True)
            return None, "创建消息失败：数据完整性错误", 400
        except Exception as e:
            db.rollback()
            logger.error(f"创建消息失败: {str(e)}", exc_info=True)
            return None, f"创建消息失败: {str(e)}", 500
    
    @staticmethod
    def get_message_by_id(
        db: Session,
        message_id: str
    ) -> Tuple[Optional[Message], Optional[str], int]:
        """
        根据ID获取消息
        
        Args:
            db: 数据库会话
            message_id: 消息ID
            
        Returns:
            Tuple[Message对象, 错误消息, HTTP状态码]
        """
        try:
            message = db.query(Message).filter(
                Message.id == message_id
            ).first()
            
            if not message:
                return None, f"未找到ID为 {message_id} 的消息", 404
            
            return message, None, 200
            
        except Exception as e:
            logger.error(f"获取消息失败: {str(e)}", exc_info=True)
            return None, f"获取消息失败: {str(e)}", 500
    
    @staticmethod
    def get_messages_by_conversation_id(
        db: Session,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by_desc: bool = True
    ) -> Tuple[List[Message], Optional[str], int]:
        """
        根据会话ID获取消息列表
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            limit: 限制返回数量（可选）
            offset: 偏移量（默认0）
            order_by_desc: 是否按创建时间倒序（默认True，最新的在前）
            
        Returns:
            Tuple[消息列表, 错误消息, HTTP状态码]
        """
        try:
            query = db.query(Message).filter(
                Message.conversation_id == conversation_id
            )
            
            if order_by_desc:
                query = query.order_by(Message.created_at.desc())
            else:
                query = query.order_by(Message.created_at.asc())
            
            if limit:
                query = query.limit(limit).offset(offset)
            
            messages = query.all()
            return messages, None, 200
            
        except Exception as e:
            logger.error(f"获取消息列表失败: {str(e)}", exc_info=True)
            return [], f"获取消息列表失败: {str(e)}", 500
    
    @staticmethod
    def mark_message_as_read(
        db: Session,
        message_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        标记消息为已读
        
        Args:
            db: 数据库会话
            message_id: 消息ID
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            message = db.query(Message).filter(
                Message.id == message_id
            ).first()
            
            if not message:
                return False, f"未找到ID为 {message_id} 的消息"
            
            if not message.is_read:
                message.is_read = True
                message.updated_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"成功标记消息 {message_id} 为已读")
            
            return True, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"标记消息为已读失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def mark_messages_as_read_by_conversation(
        db: Session,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        标记会话中的所有消息为已读
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            user_id: 用户ID（可选，如果提供则只标记该用户接收的消息）
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            query = db.query(Message).filter(
                Message.conversation_id == conversation_id,
                Message.is_read == False
            )
            
            if user_id:
                # 只标记该用户接收的消息
                query = query.filter(Message.receiver_id == user_id)
            
            messages = query.all()
            
            if messages:
                for message in messages:
                    message.is_read = True
                    message.updated_at = datetime.utcnow()
                
                db.commit()
                
                # 重置会话的未读消息数
                ConversationService.reset_unread_count(db, conversation_id)
                
                logger.info(f"成功标记会话 {conversation_id} 中的 {len(messages)} 条消息为已读")
            
            return True, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"标记消息为已读失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def mark_message_as_delivered(
        db: Session,
        message_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        标记消息为已送达
        
        Args:
            db: 数据库会话
            message_id: 消息ID
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            message = db.query(Message).filter(
                Message.id == message_id
            ).first()
            
            if not message:
                return False, f"未找到ID为 {message_id} 的消息"
            
            if not message.is_delivered:
                message.is_delivered = True
                message.updated_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"成功标记消息 {message_id} 为已送达")
            
            return True, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"标记消息为已送达失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def delete_message(
        db: Session,
        message_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        删除消息
        
        Args:
            db: 数据库会话
            message_id: 消息ID
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            message = db.query(Message).filter(
                Message.id == message_id
            ).first()
            
            if not message:
                return False, f"未找到ID为 {message_id} 的消息"
            
            db.delete(message)
            db.commit()
            
            logger.info(f"成功删除消息 {message_id}")
            return True, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"删除消息失败: {str(e)}", exc_info=True)
            return False, str(e)

