from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Tuple, Optional, Dict, Any
import logging
import random
import string
from app.models.load import Load
from app.services.role_service import RoleService

logger = logging.getLogger(__name__)


class LoadService:
    """用户服务类，处理用户相关的业务逻辑"""
    
    @staticmethod
    def get_or_create_load_by_mobile(
        db: Session,
        user_mobile: str,
        name: Optional[str] = None
    ) -> Tuple[Optional[Load], Optional[str], int, bool]:
        """
        根据手机号获取或创建用户
        如果用户存在，返回用户ID；不存在则创建并返回用户ID
        
        Args:
            db: 数据库会话
            user_mobile: 手机号（必填）
            name: 用户名（创建新用户时使用，可选）
            
        Returns:
            Tuple[Load对象, 错误消息, HTTP状态码, 是否是新用户]
            成功: (Load对象, None, 200, is_new_user)
            失败: (None, 错误消息, 状态码, False)
        """
        try:
            # 验证手机号不能为空
            if not user_mobile or not user_mobile.strip():
                return None, "手机号不能为空", 400, False
            
            # 根据手机号查询用户
            existing_load = db.query(Load).filter(
                Load.user_mobile == user_mobile.strip(),
                Load.status != 'deleted'
            ).first()
            
            # 如果用户存在，直接返回（不是新用户）
            if existing_load:
                logger.info(f"找到已存在用户: {existing_load.id} - {existing_load.user_mobile}")
                return existing_load, None, 200, False
            
            # 用户不存在，创建新用户
            # 生成随机6个大小写英文字符组成的字符串作为name
            if name and name.strip():
                load_name = name.strip()
            else:
                # 生成随机6个大小写英文字符
                load_name = ''.join(random.choices(string.ascii_letters, k=6))
            
            new_load = Load(
                user_mobile=user_mobile.strip(),
                name=load_name,
                email='',  # email可以为空
                description=None,
                status='active'
            )
            
            db.add(new_load)
            db.commit()
            db.refresh(new_load)
            
            # 不再在登录时创建role记录，等到输入昵称时再创建
            logger.info(f"成功创建新用户: {new_load.id} - {new_load.user_mobile}")
            return new_load, None, 200, True  # 返回True表示是新用户
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"数据库完整性错误: {str(e)}", exc_info=True)
            return None, "创建用户失败：数据完整性错误", 400, False
        except Exception as e:
            db.rollback()
            logger.error(f"获取或创建用户失败: {str(e)}", exc_info=True)
            return None, f"获取或创建用户失败: {str(e)}", 500, False
    
    @staticmethod
    def get_load_by_id(db: Session, load_id) -> Tuple[Optional[Load], Optional[str], int]:
        """
        根据ID获取用户
        
        Args:
            db: 数据库会话
            load_id: 用户ID（整数，可以是 int 或 str）
            
        Returns:
            Tuple[Load对象, 错误消息, HTTP状态码]
        """
        try:
            # 确保 load_id 是整数类型
            load_id_int = int(load_id) if not isinstance(load_id, int) else load_id
            load = db.query(Load).filter(Load.id == load_id_int).first()
            
            if not load:
                return None, f"未找到ID为 {load_id_int} 的用户", 404
            
            return load, None, 200
            
        except Exception as e:
            logger.error(f"获取用户失败: {str(e)}", exc_info=True)
            return None, f"获取用户失败: {str(e)}", 500
    
    
    @staticmethod
    def update_load_by_id(
        db: Session,
        load_id,  # 用户ID（整数，可以是 int 或 str）
        name: Optional[str] = None,
        description: Optional[str] = None,
        email: Optional[str] = None,
        avatar_data: Optional[str] = None,
        instance_id: Optional[str] = None,
        instance_password: Optional[str] = None,
        status: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        根据ID更新用户信息（支持更新整条记录）
        
        Args:
            db: 数据库会话
            load_id: 用户ID
            name: 用户名（可选）
            description: 描述（可选）
            email: 邮箱（可选）
            avatar_data: 头像数据（可选）
            instance_id: 实例ID（可选）
            instance_password: 实例密码（可选）
            status: 状态（可选）
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            load = db.query(Load).filter(Load.id == load_id).first()
            if not load:
                return False, f"未找到ID为 {load_id} 的用户"
            
            # 只更新提供的字段
            if name is not None:
                load.name = name.strip()
            if description is not None:
                load.description = description
            if email is not None:
                load.email = email.strip()
            if avatar_data is not None:
                load.avatar_data = avatar_data
            if instance_id is not None:
                load.instance_id = instance_id
            if instance_password is not None:
                load.instance_password = instance_password
            if status is not None:
                if status not in ['active', 'inactive', 'deleted']:
                    return False, f"无效的状态值: {status}。允许的值: active, inactive, deleted"
                load.status = status
            
            # 更新 update_time 时间戳
            from datetime import datetime
            load.update_time = datetime.utcnow()
            
            db.commit()
            # 确保 load_id 是整数类型
            load_id_int = int(load_id) if not isinstance(load_id, int) else load_id
            logger.info(f"成功更新用户 {load_id_int} 的信息")
            
            # 如果更新了 name，同步更新 roles 表中对应 load_id 的记录
            # 注意：更新description时不自动更新system_prompt，需要单独调用generate_system_prompt
            if name is not None:
                success_role, error_role, role_id = RoleService.update_role_by_uuid(
                    db=db,
                    uuid=load_id_int,
                    name=name.strip() if name is not None else None
                )
                if not success_role:
                    logger.warning(f"更新 loads 成功，但更新 roles 失败: {error_role}")
                    # 不返回错误，因为 loads 已经更新成功
            
            return True, None
        except Exception as e:
            db.rollback()
            logger.error(f"更新用户信息失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def get_description(db: Session) -> Optional[str]:
        """
        获取当前用户的描述
        
        Args:
            db: 数据库会话
            
        Returns:
            描述字符串，如果不存在返回None
        """
        try:
            current_load = db.query(Load).first()
            return current_load.description if current_load else None
        except Exception as e:
            logger.error(f"获取用户描述失败: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    def update_description_only(
        db: Session,
        load_id,  # 用户ID（整数，可以是 int 或 str）
        description: str
    ) -> Tuple[bool, Optional[str]]:
        """
        只更新用户描述，不更新system_prompt
        
        Args:
            db: 数据库会话
            load_id: 用户ID
            description: 描述
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            load = db.query(Load).filter(Load.id == load_id).first()
            if not load:
                return False, f"未找到ID为 {load_id} 的用户"
            
            # 只更新description
            load.description = description
            
            # 更新 update_time 时间戳
            from datetime import datetime
            load.update_time = datetime.utcnow()
            
            db.commit()
            # 确保 load_id 是整数类型
            load_id_int = int(load_id) if not isinstance(load_id, int) else load_id
            logger.info(f"成功更新用户 {load_id_int} 的描述（不更新system_prompt）")
            return True, None
        except Exception as e:
            db.rollback()
            logger.error(f"更新用户描述失败: {str(e)}", exc_info=True)
            return False, str(e)
    

