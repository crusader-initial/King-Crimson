from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, CheckConstraint, Boolean
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


class Memory(Base):
    """文件元数据表"""
    __tablename__ = "memories"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)  # 自增主键 (bigserial)
    role_id = Column(String(64), nullable=False, index=True)  # 角色ID（varchar(64)类型，NOT NULL）
    name = Column(String(255), nullable=False)
    size = Column(Integer, nullable=False)
    type = Column(String(50), nullable=False)
    path = Column(String(1024), nullable=False)
    meta_data = Column(String(2048), nullable=True)  # varchar(2048)
    document_id = Column(String(64), nullable=True)  # 关联到 document.id (varchar(64)类型)
    create_time = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    update_time = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    status = Column(String(50), default='active', nullable=False)  # varchar(50)
    
    __table_args__ = (
        CheckConstraint("status IN ('active', 'deleted')", name='memories_status_check'),
    )


class Document(Base):
    """文档表"""
    __tablename__ = "document"  # 表名是单数，带引号

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)  # 自增主键 (bigserial)
    name = Column(String(255), default='', nullable=False)
    title = Column(String(511), default='', nullable=False)
    extract_status = Column(String(50), default='INITIALIZED', nullable=False)  # varchar(50)
    embedding_status = Column(String(50), default='INITIALIZED', nullable=False)  # varchar(50)
    analyze_status = Column(String(50), default='INITIALIZED', nullable=False)  # varchar(50)
    mime_type = Column(String(50), default='', nullable=False)
    raw_content = Column(String(6000), nullable=True)  # varchar(6000)
    user_description = Column(String(255), default='', nullable=False)
    create_time = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    update_time = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    url = Column(String(1023), default='', nullable=False)
    document_size = Column(Integer, default=0, nullable=False)
    insight = Column(String(6000), nullable=True)  # varchar(6000)
    summary = Column(String(6000), nullable=True)  # varchar(6000)
    keywords = Column(String(1024), nullable=True)  # varchar(1024)
    role_id = Column(String(64), nullable=True, index=True)  # 角色ID（varchar(64)类型，无外键约束）
    
    __table_args__ = (
        CheckConstraint("extract_status IN ('INITIALIZED', 'SUCCESS', 'FAILED')", name='document_extract_status_check'),
        CheckConstraint("embedding_status IN ('INITIALIZED', 'SUCCESS', 'FAILED')", name='document_embedding_status_check'),
        CheckConstraint("analyze_status IN ('INITIALIZED', 'SUCCESS', 'FAILED')", name='document_analyze_status_check'),
    )
    
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    """文档切片表"""
    __tablename__ = "chunk"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)  # 自增主键 (bigserial)
    document_id = Column(Integer, ForeignKey("document.id", ondelete="CASCADE"), nullable=False)  # 关联到 document.id (int4类型)
    content = Column(String(6000), nullable=False)  # varchar(6000) NOT NULL
    has_embedding = Column(Boolean, default=False, nullable=False)  # bool DEFAULT false NOT NULL
    tags = Column(String(1024), nullable=True)  # varchar(1024) NULL
    topic = Column(String(6000), nullable=True)  # varchar(6000) DEFAULT NULL
    create_time = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)  # timestamptz DEFAULT now() NOT NULL
    
    document = relationship("Document", back_populates="chunks")

