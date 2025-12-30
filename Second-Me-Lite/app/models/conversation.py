from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from datetime import datetime
from app.core.database import Base
import uuid


class Conversation(Base):
    """会话表（conversations）"""
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('loads.id', ondelete='CASCADE'), nullable=False)  # 用户ID，关联到 loads.id
    participant_id = Column(String(36), nullable=False)  # 参与者ID（角色ID，关联到 roles.id）
    participant_type = Column(String(20), nullable=False)  # 参与者类型（如 'role'）
    title = Column(String(255), nullable=True)  # 会话标题
    last_message_at = Column(DateTime(timezone=True), nullable=True)  # 最后一条消息时间
    last_message_content = Column(Text, nullable=True)  # 最后一条消息内容
    is_pinned = Column(Boolean, default=False, nullable=False)  # 是否置顶
    is_muted = Column(Boolean, default=False, nullable=False)  # 是否静音
    unread_count = Column(Integer, default=0, nullable=False)  # 未读消息数
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'participant_id', 'participant_type', name='uq_conversation_participants'),
    )
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'participant_id': self.participant_id,
            'participant_type': self.participant_type,
            'title': self.title,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'last_message_content': self.last_message_content,
            'is_pinned': self.is_pinned,
            'is_muted': self.is_muted,
            'unread_count': self.unread_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Message(Base):
    """消息表（messages）"""
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False)  # 会话ID
    sender_id = Column(String(36), nullable=False)  # 发送者ID（可能是 user_id 或 role_id）
    receiver_id = Column(String(36), nullable=False)  # 接收者ID（可能是 user_id 或 role_id）
    content = Column(Text, nullable=False)  # 消息内容
    message_type = Column(String(20), default='text', nullable=False)  # 消息类型（text, image, file等）
    attachment_url = Column(String(255), nullable=True)  # 附件URL
    is_sent = Column(Boolean, default=True, nullable=False)  # 是否已发送
    is_delivered = Column(Boolean, default=False, nullable=False)  # 是否已送达
    is_read = Column(Boolean, default=False, nullable=False)  # 是否已读
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        CheckConstraint("message_type IN ('text', 'image', 'file', 'audio', 'video')", name='messages_type_check'),
    )
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'content': self.content,
            'message_type': self.message_type,
            'attachment_url': self.attachment_url,
            'is_sent': self.is_sent,
            'is_delivered': self.is_delivered,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

