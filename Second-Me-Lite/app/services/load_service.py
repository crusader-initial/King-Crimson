from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Tuple, Optional, Dict, Any
import logging
from app.models.load import Load

logger = logging.getLogger(__name__)


class LoadService:
    """用户服务类，处理用户相关的业务逻辑"""
    
    @staticmethod
    def create_load(
        db: Session,
        name: str,
        email: str = '',
        description: Optional[str] = None,
        avatar_data: Optional[str] = None,
        instance_id: Optional[str] = None,
        instance_password: Optional[str] = None,
        status: str = 'active'
    ) -> Tuple[Optional[Load], Optional[str], int]:
        """
        创建新用户
        
        Args:
            db: 数据库会话
            name: 用户名（必填）
            email: 邮箱（默认空字符串）
            description: 描述（可选）
            avatar_data: 头像数据（可选）
            instance_id: 实例ID（可选）
            instance_password: 实例密码（可选）
            status: 状态（默认 'active'）
            
        Returns:
            Tuple[Load对象, 错误消息, HTTP状态码]
            成功: (Load对象, None, 200)
            失败: (None, 错误消息, 状态码)
        """
        try:
            # 验证必填字段
            if not name or not name.strip():
                return None, "用户名不能为空", 400
            
            # 验证状态值
            if status not in ['active', 'inactive', 'deleted']:
                return None, f"无效的状态值: {status}。允许的值: active, inactive, deleted", 400
            
            # 检查邮箱是否已存在（如果提供了邮箱）
            if email and email.strip():
                existing_load = db.query(Load).filter(
                    Load.email == email.strip(),
                    Load.status != 'deleted'
                ).first()
                if existing_load:
                    return None, f"邮箱 {email} 已被使用", 409
            
            # 创建新用户
            new_load = Load(
                name=name.strip(),
                email=email.strip() if email else '',
                description=description.strip() if description else None,
                avatar_data=avatar_data,
                instance_id=instance_id,
                instance_password=instance_password,
                status=status
            )
            
            db.add(new_load)
            db.commit()
            db.refresh(new_load)
            
            logger.info(f"成功创建用户: {new_load.id} - {new_load.name}")
            return new_load, None, 200
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"数据库完整性错误: {str(e)}", exc_info=True)
            return None, "创建用户失败：数据完整性错误", 400
        except Exception as e:
            db.rollback()
            logger.error(f"创建用户失败: {str(e)}", exc_info=True)
            return None, f"创建用户失败: {str(e)}", 500
    
    @staticmethod
    def get_current_load(db: Session) -> Tuple[Optional[Load], Optional[str], int]:
        """
        获取当前用户（获取第一个活跃用户，或根据业务逻辑调整）
        
        Args:
            db: 数据库会话
            
        Returns:
            Tuple[Load对象, 错误消息, HTTP状态码]
        """
        try:
            # 获取第一个活跃用户（可以根据实际业务逻辑调整）
            current_load = db.query(Load).filter(
                Load.status == 'active'
            ).order_by(Load.created_at.desc()).first()
            
            if not current_load:
                return None, "未找到活跃用户", 404
            
            return current_load, None, 200
            
        except Exception as e:
            logger.error(f"获取当前用户失败: {str(e)}", exc_info=True)
            return None, f"获取当前用户失败: {str(e)}", 500
    
    @staticmethod
    def get_load_by_id(db: Session, load_id: str) -> Tuple[Optional[Load], Optional[str], int]:
        """
        根据ID获取用户
        
        Args:
            db: 数据库会话
            load_id: 用户ID
            
        Returns:
            Tuple[Load对象, 错误消息, HTTP状态码]
        """
        try:
            load = db.query(Load).filter(Load.id == load_id).first()
            
            if not load:
                return None, f"未找到ID为 {load_id} 的用户", 404
            
            return load, None, 200
            
        except Exception as e:
            logger.error(f"获取用户失败: {str(e)}", exc_info=True)
            return None, f"获取用户失败: {str(e)}", 500

