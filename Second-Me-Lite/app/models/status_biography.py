from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base

class StatusBiography(Base):
    """状态传记表"""
    __tablename__ = "status_biography"
    
    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(String(36), ForeignKey('roles.id', ondelete='SET NULL'), nullable=True)  # 根据实际数据库表结构，role_id 是 varchar(36)
    content = Column(Text, nullable=False)
    content_third_view = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    summary_third_view = Column(Text, nullable=False)
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

