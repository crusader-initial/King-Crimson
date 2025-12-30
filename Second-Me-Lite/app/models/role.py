from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime
from app.core.database import Base


class Role(Base):
    """角色表（roles）"""
    __tablename__ = "roles"
    
    id = Column(String(36), primary_key=True)  # 角色独立ID（varchar(36)），自动生成的UUID
    uuid = Column(String(64), nullable=False, unique=True)  # 用户ID（varchar(64)），关联到 loads.id，用于关联用户
    name = Column(String(100), nullable=False, unique=True)
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
            'uuid': self.uuid,
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

