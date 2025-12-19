from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.core.database import Base
import uuid

# 尝试导入 PGVector 类型支持
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # 如果 pgvector 包未安装，使用 TypeDecorator 创建自定义类型
    from sqlalchemy import TypeDecorator, String as SQLString
    from sqlalchemy.dialects.postgresql import ARRAY
    
    class Vector(TypeDecorator):
        """
        PGVector 类型的占位符
        如果 pgvector 包未安装，使用 ARRAY 类型作为后备
        注意：这需要数据库层面已经定义了 vector 类型
        """
        impl = ARRAY
        cache_ok = True
        
        def load_dialect_impl(self, dialect):
            if dialect.name == 'postgresql':
                # 使用 PostgreSQL 的 ARRAY 类型作为后备
                # 实际在数据库中应该是 vector 类型
                return dialect.type_descriptor(ARRAY(SQLString))
            return dialect.type_descriptor(SQLString)


class Memory(Base):
    """文件元数据表"""
    __tablename__ = "memories"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    size = Column(Integer, nullable=False)
    type = Column(String(50), nullable=False)
    path = Column(String(1024), nullable=False)
    meta_data = Column(Text, nullable=True)
    document_id = Column(String(36), nullable=True)  # 数据库中是 varchar(36)，存储 document.id 的字符串形式
    role_id = Column(Integer, nullable=True, index=True)  # 关联到 roles.id (Integer类型)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    status = Column(String(20), default='active', nullable=False)
    
    __table_args__ = (
        CheckConstraint("status IN ('active', 'deleted')", name='memories_status_check'),
    )


class Document(Base):
    """文档表"""
    __tablename__ = "document"  # 表名是单数，带引号

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), default='', nullable=False)
    title = Column(String(511), default='', nullable=False)
    extract_status = Column(String(20), default='INITIALIZED', nullable=False)
    embedding_status = Column(String(20), default='INITIALIZED', nullable=False)
    analyze_status = Column(String(20), default='INITIALIZED', nullable=False)
    mime_type = Column(String(50), default='', nullable=False)
    raw_content = Column(Text, nullable=True)
    user_description = Column(String(255), default='', nullable=False)
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    url = Column(String(1023), default='', nullable=False)
    document_size = Column(Integer, default=0, nullable=False)
    insight = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)
    role_id = Column(Integer, nullable=True, index=True)  # 关联到 roles.id (Integer类型)
    
    __table_args__ = (
        CheckConstraint("extract_status IN ('INITIALIZED', 'SUCCESS', 'FAILED')", name='document_extract_status_check'),
        CheckConstraint("embedding_status IN ('INITIALIZED', 'SUCCESS', 'FAILED')", name='document_embedding_status_check'),
        CheckConstraint("analyze_status IN ('INITIALIZED', 'SUCCESS', 'FAILED')", name='document_analyze_status_check'),
    )
    
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    """文档切片表"""
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("document.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=True)
    # PGVector 向量列，维度为 1024（multimodal-embedding-v1）
    embedding = Column(Vector(1024), nullable=True)
    # 使用 PostgreSQL 的 JSONB 类型
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=True)
    
    document = relationship("Document", back_populates="chunks")


class ChatHistory(Base):
    """聊天历史表"""
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(50), nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
