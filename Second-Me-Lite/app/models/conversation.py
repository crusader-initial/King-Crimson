from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import uuid


class Conversation(Base):
    """会话表（conversations）"""
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_type = Column(String(20), nullable=False)  # 'single' 单聊, 'group' 群聊
    title = Column(String(255), nullable=True)  # 群聊标题，单聊可空
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    participants = relationship("ConversationParticipant", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'conversation_type': self.conversation_type,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ConversationParticipant(Base):
    """会话参与者表（conversation_participants）"""
    __tablename__ = "conversation_participants"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String(36), nullable=False)  # 用户ID（loads.id）
    joined_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_read_at = Column(DateTime(timezone=True), nullable=True)  # 用户最后阅读时间
    
    # 关系
    conversation = relationship("Conversation", back_populates="participants")
    
    __table_args__ = (
        UniqueConstraint('conversation_id', 'user_id', name='uq_conversation_user'),
    )
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'user_id': self.user_id,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'last_read_at': self.last_read_at.isoformat() if self.last_read_at else None,
        }


class Message(Base):
    """消息表（messages）"""
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False)
    sender_id = Column(String(36), nullable=False)  # 发送者ID（user_id 或 role_id）
    content = Column(Text, nullable=False)  # 消息内容
    message_type = Column(String(20), default='text', nullable=False)  # 消息类型（text, image, file等）
    attachment_url = Column(String(255), nullable=True)  # 附件URL
    sender_type = Column(String(10), default='user', nullable=False)  # 'user' 真实用户, 'ai' AI用户
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    conversation = relationship("Conversation", back_populates="messages")
    
    __table_args__ = (
        CheckConstraint("message_type IN ('text', 'image', 'file', 'audio', 'video')", name='messages_type_check'),
        CheckConstraint("sender_type IN ('user', 'ai')", name='messages_sender_type_check'),
    )
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'sender_id': self.sender_id,
            'content': self.content,
            'message_type': self.message_type,
            'attachment_url': self.attachment_url,
            'sender_type': self.sender_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

