from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_, func
from typing import Tuple, Optional, List
from datetime import datetime
import logging
from app.models.conversation import Conversation, ConversationParticipant, Message

logger = logging.getLogger(__name__)


class ConversationService:
    """会话服务类，处理会话相关的业务逻辑"""
    
    @staticmethod
    def get_or_create_conversation(
        db: Session,
        participant_ids: List[str],
        conversation_type: str = 'single',
        title: Optional[str] = None
    ) -> Tuple[Optional[Conversation], Optional[str], int]:
        """
        获取或创建会话（支持单聊和群聊）
        如果会话存在（包含所有指定的参与者），返回现有会话；不存在则创建新会话
        
        Args:
            db: 数据库会话
            participant_ids: 参与者ID列表（loads.id 或 roles.id 的列表）
            conversation_type: 会话类型（'single' 单聊, 'group' 群聊，默认 'single'）
            title: 会话标题（可选）
            
        Returns:
            Tuple[Conversation对象, 错误消息, HTTP状态码]
            成功: (Conversation对象, None, 200)
            失败: (None, 错误消息, 状态码)
        """
        try:
            # 验证必填字段
            if not participant_ids or len(participant_ids) == 0:
                return None, "参与者ID列表不能为空", 400
            
            # 去重并清理
            participant_ids = list(set([pid.strip() for pid in participant_ids if pid and pid.strip()]))
            
            if len(participant_ids) == 0:
                return None, "参与者ID列表不能为空", 400
            
            # 验证会话类型
            if conversation_type not in ['single', 'group']:
                return None, f"无效的会话类型: {conversation_type}。允许的类型: 'single', 'group'", 400
            
            # 对于单聊，必须恰好有2个参与者
            if conversation_type == 'single' and len(participant_ids) != 2:
                return None, f"单聊会话必须恰好有2个参与者，当前有 {len(participant_ids)} 个", 400
            
            # 查找包含所有指定参与者的会话
            existing_conversation = db.query(Conversation).join(
                ConversationParticipant
            ).filter(
                Conversation.conversation_type == conversation_type,
                ConversationParticipant.user_id.in_(participant_ids)
            ).group_by(Conversation.id).having(
                func.count(ConversationParticipant.user_id.distinct()) == len(participant_ids)
            ).first()
            
            if existing_conversation:
                logger.info(f"找到已存在会话: {existing_conversation.id} - 参与者: {participant_ids}")
                return existing_conversation, None, 200
            
            # 创建新会话
            new_conversation = Conversation(
                conversation_type=conversation_type,
                title=title.strip() if title else None
            )
            db.add(new_conversation)
            db.flush()  # 获取conversation.id
            
            # 为所有参与者创建记录
            # 注意：conversation_participants.user_id 字段存储的是参与者ID，可能是用户ID（loads.id）或角色ID（roles.id）
            for participant_id in participant_ids:
                participant = ConversationParticipant(
                    conversation_id=new_conversation.id,
                    user_id=participant_id  # 参与者ID（loads.id 或 roles.id）
                )
                db.add(participant)
            
            db.commit()
            db.refresh(new_conversation)
            
            # 验证插入的数据
            inserted_participants = db.query(ConversationParticipant).filter(
                ConversationParticipant.conversation_id == new_conversation.id
            ).all()
            logger.info(f"成功创建新会话: {new_conversation.id} - 类型: {conversation_type}")
            logger.info(f"  - 参与者列表: {participant_ids}")
            logger.info(f"  - 实际插入的参与者数量: {len(inserted_participants)}")
            for p in inserted_participants:
                logger.info(f"    * participant_id={p.id}, user_id={p.user_id}")
            
            return new_conversation, None, 200
            
        except IntegrityError as e:
            db.rollback()
            # 如果是因为唯一约束冲突，尝试再次查询
            if "uq_conversation_user" in str(e):
                existing_conversation = db.query(Conversation).join(
                    ConversationParticipant
                ).filter(
                    Conversation.conversation_type == conversation_type,
                    ConversationParticipant.user_id.in_(participant_ids)
                ).group_by(Conversation.id).having(
                    func.count(ConversationParticipant.user_id.distinct()) == len(participant_ids)
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
        conversation_type: str = 'single'
    ) -> Tuple[Optional[Conversation], Optional[str], int]:
        """
        获取两个参与者之间的会话（无论谁发起）
        
        Args:
            db: 数据库会话
            participant1_id: 参与者1的ID
            participant2_id: 参与者2的ID
            conversation_type: 会话类型（默认 'single'）
            
        Returns:
            Tuple[Conversation对象, 错误消息, HTTP状态码]
        """
        try:
            conversation = db.query(Conversation).join(
                ConversationParticipant
            ).filter(
                Conversation.conversation_type == conversation_type,
                ConversationParticipant.user_id.in_([participant1_id, participant2_id])
            ).group_by(Conversation.id).having(
                func.count(ConversationParticipant.user_id.distinct()) == 2
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
            # 通过conversation_participants表查找用户参与的所有会话
            query = db.query(Conversation).join(
                ConversationParticipant
            ).filter(
                ConversationParticipant.user_id == user_id
            ).order_by(
                Conversation.updated_at.desc()
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
        title: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        更新会话信息
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            title: 会话标题（可选）
            
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
        更新会话的最后一条消息信息（通过更新updated_at来反映最后消息时间）
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            last_message_content: 最后一条消息内容（保留参数以兼容旧代码）
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                return False, f"未找到ID为 {conversation_id} 的会话"
            
            conversation.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"成功更新会话 {conversation_id} 的最后一条消息")
            return True, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"更新会话最后消息失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def get_conversation_participants(
        db: Session,
        conversation_id: str
    ) -> Tuple[List[ConversationParticipant], Optional[str], int]:
        """
        获取会话的所有参与者
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            
        Returns:
            Tuple[参与者列表, 错误消息, HTTP状态码]
        """
        try:
            participants = db.query(ConversationParticipant).filter(
                ConversationParticipant.conversation_id == conversation_id
            ).all()
            
            return participants, None, 200
            
        except Exception as e:
            logger.error(f"获取会话参与者失败: {str(e)}", exc_info=True)
            return [], f"获取会话参与者失败: {str(e)}", 500
    
    @staticmethod
    def update_participant_last_read(
        db: Session,
        conversation_id: str,
        user_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        更新参与者的最后阅读时间
        
        Args:
            db: 数据库会话
            conversation_id: 会话ID
            user_id: 用户ID
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            participant = db.query(ConversationParticipant).filter(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id
            ).first()
            
            if not participant:
                return False, f"未找到会话 {conversation_id} 中用户 {user_id} 的参与者记录"
            
            participant.last_read_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"成功更新参与者 {user_id} 在会话 {conversation_id} 的最后阅读时间")
            return True, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"更新参与者最后阅读时间失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def delete_conversation(
        db: Session,
        conversation_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        删除会话（级联删除相关消息和参与者）
        
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
