from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Tuple, Optional, List
import logging
import uuid
from app.models.role import Role
from app.services.l1_bio_service import L1BioService

logger = logging.getLogger(__name__)


class RoleService:
    """角色服务类，处理角色相关的业务逻辑"""
    
    @staticmethod
    def _build_system_prompt(
        load_name: str,
        role_name: str,
        role_description: str
    ) -> str:
        """
        构建system_prompt的公共方法
        
        Args:
            load_name: 用户名称（loads.name）
            role_name: 角色名称（roles.name）
            role_description: 角色描述（roles.description或传入的description）
            
        Returns:
            system_prompt字符串
        """
        return f"""你是{load_name}的"第二自我"，这是由{load_name}创建的个性化AI。你作为{load_name}的代表，代表{load_name}与他人互动。目前，你正在以{role_name}的角色与外部用户互动。你的职责是{role_description}。"""
    
    @staticmethod
    def create_role(
        db: Session,
        user_uuid,  # 用户ID（loads.id），可以是 int 或 str
        name: str,
        description: Optional[str] = None,
        system_prompt: str = "",
        icon: Optional[str] = None,
        is_active: bool = True,
        enable_l0_retrieval: bool = True,
        enable_l1_retrieval: bool = True,
        load_name: Optional[str] = None
    ) -> Tuple[Optional[Role], Optional[str], int]:
        """
        创建新角色
        
        Args:
            db: 数据库会话
            user_uuid: 用户ID（loads.id，整数），将存储到 roles.load_id 用于关联用户
            name: 角色名称（必填）
            description: 描述（可选）
            system_prompt: 系统提示词（必填，默认空字符串，如果为空且load_name存在则自动生成）
            icon: 图标（可选）
            is_active: 是否激活（默认True）
            enable_l0_retrieval: 是否启用L0检索（默认True）
            enable_l1_retrieval: 是否启用L1检索（默认True）
            load_name: 用户名称（可选，用于生成默认system_prompt）
            
        Returns:
            Tuple[Role对象, 错误消息, HTTP状态码]
            成功: (Role对象, None, 200)
            失败: (None, 错误消息, 状态码)
            
        注意：
            - roles.id 是独立的UUID，自动生成
            - roles.load_id 存储传入的 loads.id（整数），用于关联用户
        """
        try:
            # 验证必填字段
            if user_uuid is None:
                return None, "用户ID不能为空", 400
            
            
            # 将 user_uuid 转换为整数
            try:
                load_id_int = int(user_uuid) if not isinstance(user_uuid, int) else user_uuid
            except (ValueError, TypeError):
                return None, f"无效的用户ID格式: {user_uuid}", 400
            
            # 检查用户ID是否已存在角色
            existing_role = db.query(Role).filter(Role.load_id == load_id_int).first()
            if existing_role:
                logger.info(f"角色已存在，用户ID: {load_id_int}")
                return existing_role, None, 200
            
            # 如果 system_prompt 为空且 load_name 存在，生成默认的 system_prompt
            final_system_prompt = system_prompt
            if not system_prompt and load_name:
                # 生成默认的 system_prompt
                role_name = name.strip() if name else '{{role}}'
                role_description = description.strip() if description else '{{responsibility}}'
                final_system_prompt = RoleService._build_system_prompt(
                    load_name=load_name,
                    role_name=role_name,
                    role_description=role_description
                )
            
            # 创建新角色
            # roles.id 是自增整数，由数据库自动生成
            # roles.load_id 用于关联 loads.id（用户ID，整数）
            # 将 user_uuid 转换为整数（如果是字符串）
            try:
                load_id_int = int(user_uuid.strip()) if isinstance(user_uuid, str) else user_uuid
            except (ValueError, AttributeError):
                return None, f"无效的用户ID格式: {user_uuid}", 400
            
            new_role = Role(
                # id 由数据库自动生成（自增整数）
                load_id=load_id_int,  # load_id 存储 loads.id（整数），用于关联用户
                name=name.strip(),
                description=description.strip() if description else None,
                system_prompt=final_system_prompt,
                icon=icon,
                is_active=is_active,
                enable_l0_retrieval=enable_l0_retrieval,
                enable_l1_retrieval=enable_l1_retrieval
            )
            
            db.add(new_role)
            db.commit()
            db.refresh(new_role)
            
            logger.info(f"成功创建角色: {new_role.id} - {new_role.name} (load_id: {new_role.load_id})")
            return new_role, None, 200
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"数据库完整性错误: {str(e)}", exc_info=True)
            return None, "创建角色失败：数据完整性错误", 400
        except Exception as e:
            db.rollback()
            logger.error(f"创建角色失败: {str(e)}", exc_info=True)
            return None, f"创建角色失败: {str(e)}", 500
    
    @staticmethod
    def get_role_by_id(db: Session, role_id: int) -> Tuple[Optional[Role], Optional[str], int]:
        """
        根据角色ID获取角色（根据 roles.id 查询）
        
        Args:
            db: 数据库会话
            role_id: 角色ID（roles.id）
            
        Returns:
            Tuple[Role对象, 错误消息, HTTP状态码]
        """
        try:
            role = db.query(Role).filter(Role.id == role_id).first()
            
            if not role:
                return None, f"未找到ID为 {role_id} 的角色", 404
            
            return role, None, 200
            
        except Exception as e:
            logger.error(f"获取角色失败: {str(e)}", exc_info=True)
            return None, f"获取角色失败: {str(e)}", 500
    
    @staticmethod
    def get_role_by_uuid(db: Session, uuid) -> Tuple[Optional[Role], Optional[str], int]:
        """
        根据用户ID获取角色（根据 roles.load_id 查询，用于根据 loads.id 查找角色）
        
        Args:
            db: 数据库会话
            uuid: 用户ID（loads.id，整数，对应 roles.load_id）
            
        Returns:
            Tuple[Role对象, 错误消息, HTTP状态码]
        """
        try:
            role = db.query(Role).filter(Role.load_id == uuid).first()
            
            if not role:
                return None, f"未找到UUID为 {uuid} 的角色", 404
            
            return role, None, 200
            
        except Exception as e:
            logger.error(f"获取角色失败: {str(e)}", exc_info=True)
            return None, f"获取角色失败: {str(e)}", 500
    
    
    @staticmethod
    def update_role_by_id(
        db: Session,
        role_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        icon: Optional[str] = None,
        is_active: Optional[bool] = None,
        enable_l0_retrieval: Optional[bool] = None,
        enable_l1_retrieval: Optional[bool] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        根据角色ID更新角色信息（根据 roles.id 查询和更新）
        
        Args:
            db: 数据库会话
            role_id: 角色ID（roles.id）
            name: 角色名称（可选）
            description: 描述（可选）
            system_prompt: 系统提示词（可选）
            icon: 图标（可选）
            is_active: 是否激活（可选）
            enable_l0_retrieval: 是否启用L0检索（可选）
            enable_l1_retrieval: 是否启用L1检索（可选）
            
        Returns:
            Tuple[是否成功, 错误信息, 角色ID]
        """
        try:
            role = db.query(Role).filter(Role.id == role_id).first()
            
            if not role:
                return False, f"未找到ID为 {role_id} 的角色", None
            
            # 更新角色信息
            if name is not None:
                role.name = name.strip()
                
                # 创建l1_versions和l1_bios的初始记录（如果不存在）
                # 这个方法内部会检查是否已存在，避免重复创建
                success_l1, error_l1 = L1BioService.create_initial_l1_version_and_bio(
                    db=db,
                    role_id=role.id
                )
                if not success_l1:
                    logger.warning(f"更新角色name成功，但创建l1_versions和l1_bios失败: {error_l1}")
                    # 不返回错误，因为角色已经更新成功
            
            if description is not None:
                role.description = description.strip() if description else None
            
            if system_prompt is not None:
                role.system_prompt = system_prompt
            
            if icon is not None:
                role.icon = icon
            
            if is_active is not None:
                role.is_active = is_active
            
            if enable_l0_retrieval is not None:
                role.enable_l0_retrieval = enable_l0_retrieval
            
            if enable_l1_retrieval is not None:
                role.enable_l1_retrieval = enable_l1_retrieval
            
            # 更新 update_time 时间戳
            from datetime import datetime
            role.update_time = datetime.utcnow()
            
            db.commit()
            db.refresh(role)
            
            # 返回角色ID
            logger.info(f"成功更新ID为 {role_id} 的角色信息")
            return True, None, role_id
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"数据库完整性错误: {str(e)}", exc_info=True)
            return False, "更新角色失败：数据完整性错误", None
        except Exception as e:
            db.rollback()
            logger.error(f"更新角色信息失败: {str(e)}", exc_info=True)
            return False, str(e), None
    
    @staticmethod
    def update_role_by_uuid(
        db: Session,
        uuid,
        name: Optional[str] = None,
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        icon: Optional[str] = None,
        is_active: Optional[bool] = None,
        enable_l0_retrieval: Optional[bool] = None,
        enable_l1_retrieval: Optional[bool] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        根据用户ID更新角色信息（根据 roles.load_id 查询，一个用户只有一个角色）
        如果角色不存在，则创建新角色（用于输入昵称时创建role记录）
        
        Args:
            db: 数据库会话
            uuid: 用户ID（loads.id，整数，对应 roles.load_id）
            name: 角色名称（可选，创建时必填）
            description: 描述（可选）
            system_prompt: 系统提示词（可选）
            icon: 图标（可选）
            is_active: 是否激活（可选）
            enable_l0_retrieval: 是否启用L0检索（可选）
            enable_l1_retrieval: 是否启用L1检索（可选）
            
        Returns:
            Tuple[是否成功, 错误信息, 角色ID]
        """
        try:
            # 确保 uuid 是整数类型
            load_id_int = int(uuid) if not isinstance(uuid, int) else uuid
            role = db.query(Role).filter(Role.load_id == load_id_int).first()
            
            # 如果角色不存在，创建新角色
            if not role:
                # 创建角色时需要name
                if not name or not name.strip():
                    return False, f"创建角色时name不能为空", None
                
                # 获取loads信息以获取loads.name（用于生成system_prompt）
                from app.models.load import Load
                load = db.query(Load).filter(Load.id == load_id_int).first()
                if not load:
                    return False, f"未找到ID为 {uuid} 的用户", None
                
                # 创建新角色
                # 注意：roles.id 会自动生成自增整数，roles.load_id = loads.id
                # 此时不生成system_prompt，等到信息采集完成时才生成
                role, role_error, role_status = RoleService.create_role(
                    db=db,
                    user_uuid=load_id_int,
                    name=name.strip(),
                    description=description.strip() if description else None,
                    system_prompt="",  # 暂时为空，等信息采集完成时再生成
                    icon=icon,
                    is_active=is_active if is_active is not None else True,
                    enable_l0_retrieval=enable_l0_retrieval if enable_l0_retrieval is not None else True,
                    enable_l1_retrieval=enable_l1_retrieval if enable_l1_retrieval is not None else True,
                    load_name=None  # 不传入load_name，这样不会自动生成system_prompt
                )
                
                if role_error and role_status != 200:
                    return False, f"创建角色失败: {role_error}", None
                
                # 创建成功后，刷新role对象
                role = db.query(Role).filter(Role.load_id == load_id_int).first()
                if not role:
                    return False, "创建角色后无法找到角色记录", None
                
                # 如果创建了新角色，且传入了其他字段，需要更新这些字段
                # 但name已经在创建时设置了，跳过
                update_needed = False
                if description is not None and description != role.description:
                    role.description = description.strip() if description else None
                    update_needed = True
                if system_prompt is not None and system_prompt != role.system_prompt:
                    role.system_prompt = system_prompt
                    update_needed = True
                if icon is not None and icon != role.icon:
                    role.icon = icon
                    update_needed = True
                if is_active is not None and is_active != role.is_active:
                    role.is_active = is_active
                    update_needed = True
                if enable_l0_retrieval is not None and enable_l0_retrieval != role.enable_l0_retrieval:
                    role.enable_l0_retrieval = enable_l0_retrieval
                    update_needed = True
                if enable_l1_retrieval is not None and enable_l1_retrieval != role.enable_l1_retrieval:
                    role.enable_l1_retrieval = enable_l1_retrieval
                    update_needed = True
                
                if update_needed:
                    from datetime import datetime
                    role.update_time = datetime.utcnow()
                    db.commit()
                    db.refresh(role)
                
                # 返回角色ID
                role_id = role.id
                logger.info(f"成功创建用户ID为 {load_id_int} 的角色，角色ID: {role_id}")
                return True, None, role_id
            
            # 更新角色信息（角色已存在的情况）
            if name is not None:
                # 允许名称重复，直接更新
                role.name = name.strip()
                
                # 创建l1_versions和l1_bios的初始记录（如果不存在）
                # 这个方法内部会检查是否已存在，避免重复创建
                success_l1, error_l1 = L1BioService.create_initial_l1_version_and_bio(
                    db=db,
                    role_id=role.id
                )
                if not success_l1:
                    logger.warning(f"更新角色name成功，但创建l1_versions和l1_bios失败: {error_l1}")
                    # 不返回错误，因为角色已经更新成功
            
            if description is not None:
                role.description = description.strip() if description else None
            
            if system_prompt is not None:
                role.system_prompt = system_prompt
            
            if icon is not None:
                role.icon = icon
            
            if is_active is not None:
                role.is_active = is_active
            
            if enable_l0_retrieval is not None:
                role.enable_l0_retrieval = enable_l0_retrieval
            
            if enable_l1_retrieval is not None:
                role.enable_l1_retrieval = enable_l1_retrieval
            
            # 更新 update_time 时间戳
            from datetime import datetime
            role.update_time = datetime.utcnow()
            
            db.commit()
            db.refresh(role)
            
            # 返回角色ID
            role_id = role.id
            logger.info(f"成功更新用户ID为 {load_id_int} 的角色信息，角色ID: {role_id}")
            return True, None, role_id
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"数据库完整性错误: {str(e)}", exc_info=True)
            return False, "更新角色失败：数据完整性错误", None
        except Exception as e:
            db.rollback()
            logger.error(f"更新角色信息失败: {str(e)}", exc_info=True)
            return False, str(e), None
    
    @staticmethod
    def submit_info_collection(
        db: Session,
        uuid,
        description: str,
        system_prompt: str,
        content: Optional[str] = None,
        content_third_view: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        提交信息采集数据：更新roles表
        
        Args:
            db: 数据库会话
            uuid: 用户ID（loads.id，整数）
            description: 描述（职业和喜好）
            system_prompt: 系统提示词（由前端生成）
            content: 用户最近在做什么（已废弃，不再存储）
            content_third_view: AI生成的性格评价和MBTI（已废弃，不再存储）
            
        Returns:
            Tuple[是否成功, 错误信息, 角色ID]
        """
        try:
            # 确保 uuid 是整数类型
            load_id_int = int(uuid) if not isinstance(uuid, int) else uuid
            # 获取角色信息
            role = db.query(Role).filter(Role.load_id == load_id_int).first()
            if not role:
                return False, f"未找到用户ID为 {load_id_int} 的角色", None
            
            # 更新roles表（description和system_prompt）
            success_role, error_role, role_id = RoleService.update_role_by_uuid(
                db=db,
                uuid=load_id_int,
                description=description if description else None,
                system_prompt=system_prompt
            )
            
            if not success_role:
                return False, f"更新roles表失败: {error_role}", None
            
            db.commit()
            
            # 刷新角色对象以获取最新数据
            role = db.query(Role).filter(Role.load_id == load_id_int).first()
            role_id = role.id if role else None
            
            logger.info(f"成功提交信息采集数据: load_id={load_id_int}, role_id={role_id}")
            return True, None, role_id
        except Exception as e:
            db.rollback()
            logger.error(f"提交信息采集数据失败: {str(e)}", exc_info=True)
            return False, str(e), None
    
    @staticmethod
    def generate_system_prompt(
        db: Session,
        uuid  # 用户ID（loads.id），可以是 int 或 str
    ) -> Tuple[bool, Optional[str]]:
        """
        根据角色的description生成system_prompt并更新到roles表
        注意：此方法使用role.description，如果role.description为空，则从loads.description获取
        
        Args:
            db: 数据库会话
            uuid: 用户ID（loads.id，整数）
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            # 确保 uuid 是整数类型
            load_id_int = int(uuid) if not isinstance(uuid, int) else uuid
            # 获取角色信息
            role = db.query(Role).filter(Role.load_id == load_id_int).first()
            if not role:
                return False, f"未找到用户ID为 {load_id_int} 的角色"
            
            # 获取用户信息（用于生成system_prompt中的loads.name）
            from app.models.load import Load
            load = db.query(Load).filter(Load.id == load_id_int).first()
            if not load:
                return False, f"未找到ID为 {load_id_int} 的用户"
            
            # 使用role.description，如果为空则使用load.description
            role_description = role.description if role.description else (load.description if load.description else '{{responsibility}}')
            
            # 生成system_prompt
            role_name = role.name if role.name else '{{role}}'
            
            system_prompt = RoleService._build_system_prompt(
                load_name=load.name,
                role_name=role_name,
                role_description=role_description
            )
            
            # 更新角色的system_prompt
            success_role, error_role, role_id = RoleService.update_role_by_uuid(
                db=db,
                uuid=load_id_int,
                system_prompt=system_prompt
            )
            
            if not success_role:
                return False, f"更新system_prompt失败: {error_role}"
            
            logger.info(f"成功为用户 {load_id_int} 生成并更新system_prompt")
            return True, None
        except Exception as e:
            db.rollback()
            logger.error(f"生成system_prompt失败: {str(e)}", exc_info=True)
            return False, str(e)
    

