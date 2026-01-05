from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
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


class L1Version(Base):
    """L1版本表"""
    __tablename__ = "l1_versions"
    
    version = Column(Integer, primary_key=True, index=True)
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    role_id = Column(Integer, nullable=True)  # 角色ID，关联到 roles.load_id (loads.id，整数)


class L1Bio(Base):
    """L1传记表"""
    __tablename__ = "l1_bios"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    version = Column(Integer, ForeignKey("l1_versions.version", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, nullable=True)  # 角色ID，关联到 roles.load_id (loads.id，整数)
    content = Column(Text, nullable=True)  # 第二人称视角内容
    content_third_view = Column(Text, nullable=True)  # 第三人称视角内容
    summary = Column(Text, nullable=True)  # 第二人称视角摘要
    summary_third_view = Column(Text, nullable=True)  # 第三人称视角摘要
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)


class L1Shade(Base):
    """L1 Shade表"""
    __tablename__ = "l1_shades"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    version = Column(Integer, ForeignKey("l1_versions.version", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, nullable=True)  # 角色ID，关联到 roles.load_id (loads.id，整数)
    name = Column(String(200), nullable=True)
    aspect = Column(String(200), nullable=True)
    icon = Column(String(100), nullable=True)
    desc_third_view = Column(Text, nullable=True)
    content_third_view = Column(Text, nullable=True)
    desc_second_view = Column(Text, nullable=True)
    content_second_view = Column(Text, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)


class L1Cluster(Base):
    """L1聚类表"""
    __tablename__ = "l1_clusters"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    version = Column(Integer, ForeignKey("l1_versions.version", ondelete="CASCADE"), nullable=False, index=True)
    cluster_id = Column(String(100), nullable=True)
    memory_ids = Column(Text, nullable=True)  # JSON字符串或逗号分隔的ID列表
    cluster_center = Column(Vector(1536), nullable=True)  # 聚类中心向量（使用 pgvector 扩展）
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)


class L1ChunkTopic(Base):
    """L1 Chunk Topics表"""
    __tablename__ = "l1_chunk_topics"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    version = Column(Integer, ForeignKey("l1_versions.version", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String(100), nullable=True)
    topic = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON字符串或逗号分隔的标签
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)

