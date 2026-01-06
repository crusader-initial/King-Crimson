from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base

class StatusBiography(Base):
    """状态传记表"""
    __tablename__ = "status_biography"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)  # 自增主键 (bigserial)
    role_id = Column(String(64), nullable=True)  # 角色ID（varchar(64)类型，无外键约束）
    content = Column(String(6000), nullable=False)  # varchar(6000)
    content_third_view = Column(String(6000), nullable=False)  # varchar(6000)
    summary = Column(String(6000), nullable=False)  # varchar(6000)
    summary_third_view = Column(String(6000), nullable=False)  # varchar(6000)
    create_time = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    update_time = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

