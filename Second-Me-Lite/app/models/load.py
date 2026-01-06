from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, CheckConstraint
from datetime import datetime
from app.core.database import Base


class Load(Base):
    """用户表（loads）"""
    __tablename__ = "loads"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)  # 自增主键 (bigserial)
    name = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=True)  # varchar(2000)
    email = Column(String(255), nullable=False, default='')
    avatar_data = Column(String(255), nullable=True)  # varchar(255)
    instance_id = Column(String(255), nullable=True)
    instance_password = Column(String(255), nullable=True)
    status = Column(String(50), default='active', nullable=True)  # varchar(50)
    create_time = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    update_time = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
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
            'created_at': self.create_time.isoformat() if self.create_time else None,
            'updated_at': self.update_time.isoformat() if self.update_time else None,
        }

