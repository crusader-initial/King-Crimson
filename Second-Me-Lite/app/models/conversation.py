from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Conversation(Base):
    """会话表（conversations）"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_type = Column(String(20), nullable=False)  # 'single' 单聊, 'group' 群聊
    title = Column(String(255), nullable=True)  # 群聊标题，单聊可空
    create_time = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    update_time = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    # 注意：由于conversation_id是String类型，不能使用标准外键关系
    # 关系定义已移除，代码中使用直接查询代替关系访问
    # 如需使用关系，请使用: db.query(ConversationParticipant).filter(ConversationParticipant.conversation_id == str(conversation.id))
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'conversation_type': self.conversation_type,
            'title': self.title,
            'created_at': self.create_time.isoformat() if self.create_time else None,  # API兼容性：返回created_at
            'updated_at': self.update_time.isoformat() if self.update_time else None,  # API兼容性：返回updated_at
        }


class ConversationParticipant(Base):
    """会话参与者表（conversation_participants）"""
    __tablename__ = "conversation_participants"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=False)  # 会话ID（varchar类型，存储conversations.id的字符串形式）
    user_id = Column(String(64), nullable=False)  # 用户ID（loads.id）或角色ID（roles.id），varchar类型
    joined_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_read_at = Column(DateTime(timezone=True), nullable=True)  # 用户最后阅读时间
    
    # 关系
    # 注意：由于conversation_id是String类型，不能使用标准外键关系
    # conversation = relationship("Conversation", back_populates="participants")
    
    # 注意：由于conversation_id是String类型，不能使用ForeignKey约束
    # 需要在应用层保证数据一致性
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
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)  # 自增主键 (bigserial)
    conversation_id = Column(String(64), nullable=False)  # 会话ID（varchar类型，存储conversations.id的字符串形式）
    sender_id = Column(String(64), nullable=False)  # 发送者ID（loads.id 或 roles.id），varchar类型
    content = Column(String(10000), nullable=False)  # 消息内容 (varchar(10000))
    message_type = Column(String(20), default='text', nullable=False)  # 消息类型（text, image, file等）
    attachment_url = Column(String(255), nullable=True)  # 附件URL
    sender_type = Column(String(10), default='user', nullable=False)  # 'user' 真实用户, 'ai' AI用户
    create_time = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    update_time = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    # 注意：由于conversation_id是String类型，不能使用标准外键关系
    # conversation = relationship("Conversation", back_populates="messages")
    
    __table_args__ = (
        CheckConstraint("message_type IN ('text', 'image', 'file', 'audio', 'video')", name='messages_type_check'),
        CheckConstraint("sender_type IN ('user', 'ai')", name='messages_sender_type_check'),
        Index('idx_message_sender_created_at', 'sender_id', 'create_time'),
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
            'created_at': self.create_time.isoformat() if self.create_time else None,  # API兼容性：返回created_at
            'updated_at': self.update_time.isoformat() if self.update_time else None,  # API兼容性：返回updated_at
        }

