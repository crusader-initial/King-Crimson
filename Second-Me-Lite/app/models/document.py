from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.core.database import Base

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

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)  # Raw content
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer)
    # PGVector 向量列，维度为 1024（multimodal-embedding-v1）
    embedding = Column(Vector(1024), nullable=True)  # 修改这里：1536 -> 1024
    # 使用 PostgreSQL 的 JSONB 类型（而不是 TEXT）
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("Document", back_populates="chunks")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(50), nullable=False) # user / assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
