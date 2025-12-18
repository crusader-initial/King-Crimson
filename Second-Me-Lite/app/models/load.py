from sqlalchemy import Column, String, Text, DateTime, CheckConstraint
from datetime import datetime
from app.core.database import Base
import uuid


class Load(Base):
    """用户表（loads）"""
    __tablename__ = "loads"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    email = Column(String(255), nullable=False, default='')
    avatar_data = Column(Text, nullable=True)
    instance_id = Column(String(255), nullable=True)
    instance_password = Column(String(255), nullable=True)
    status = Column(String(20), default='active', nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    user_mobile = Column(String(20), nullable=True)  # 手机号字段
    
    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive', 'deleted')", name='loads_status_check'),
    )
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'email': self.email,
            'avatar_data': self.avatar_data,
            'instance_id': self.instance_id,
            'status': self.status,
            'user_mobile': self.user_mobile,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

