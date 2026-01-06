from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base


class Role(Base):
    """角色表（roles）"""
    __tablename__ = "roles"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)  # 自增主键 (bigserial)
    load_id = Column(String(64), ForeignKey('loads.id', ondelete='CASCADE'), nullable=False, unique=True)  # 用户ID，关联到 loads.id（varchar类型）
    name = Column(String(100), nullable=False)  # 角色名称，允许重复
    description = Column(String(500), nullable=True)
    system_prompt = Column(String(6000), nullable=False)  # varchar(6000)
    icon = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    enable_l0_retrieval = Column(Boolean, default=False, nullable=False)  # 默认值为 false
    enable_l1_retrieval = Column(Boolean, default=True, nullable=False)
    create_time = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    update_time = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'load_id': self.load_id,
            'name': self.name,
            'description': self.description,
            'system_prompt': self.system_prompt,
            'icon': self.icon,
            'is_active': self.is_active,
            'enable_l0_retrieval': self.enable_l0_retrieval,
            'enable_l1_retrieval': self.enable_l1_retrieval,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None,
        }

