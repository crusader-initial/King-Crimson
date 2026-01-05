from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base


class Role(Base):
    """角色表（roles）"""
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # 角色独立ID，自增整数
    load_id = Column(Integer, ForeignKey('loads.id', ondelete='CASCADE'), nullable=False, unique=True)  # 用户ID，关联到 loads.id，用于关联用户
    name = Column(String(100), nullable=False)  # 角色名称，允许重复
    description = Column(String(500), nullable=True)
    system_prompt = Column(Text, nullable=False)
    icon = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    enable_l0_retrieval = Column(Boolean, default=True, nullable=False)
    enable_l1_retrieval = Column(Boolean, default=True, nullable=False)
    create_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
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

