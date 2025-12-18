from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Tuple, Optional, List
import logging
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
        uuid: str,
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
            uuid: 角色UUID（对应loads.id）
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
        """
        try:
            # 验证必填字段
            if not uuid or not uuid.strip():
                return None, "UUID不能为空", 400
            
            
            # 检查UUID是否已存在
            existing_role = db.query(Role).filter(Role.uuid == uuid.strip()).first()
            if existing_role:
                logger.info(f"角色已存在，UUID: {uuid}")
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
            # 注意：id 和 uuid 都存储 loads.id（UUID字符串），根据实际数据库表结构
            new_role = Role(
                id=uuid.strip(),  # id 存储 loads.id（UUID字符串，varchar(36)）
                uuid=uuid.strip(),  # uuid 存储 loads.id（UUID字符串，varchar(64)）
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
            
            logger.info(f"成功创建角色: {new_role.id} - {new_role.name} (UUID: {new_role.uuid})")
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
    def get_role_by_uuid(db: Session, uuid: str) -> Tuple[Optional[Role], Optional[str], int]:
        """
        根据UUID获取角色
        
        Args:
            db: 数据库会话
            uuid: 角色UUID
            
        Returns:
            Tuple[Role对象, 错误消息, HTTP状态码]
        """
        try:
            role = db.query(Role).filter(Role.uuid == uuid).first()
            
            if not role:
                return None, f"未找到UUID为 {uuid} 的角色", 404
            
            return role, None, 200
            
        except Exception as e:
            logger.error(f"获取角色失败: {str(e)}", exc_info=True)
            return None, f"获取角色失败: {str(e)}", 500
    
    
    @staticmethod
    def update_role_by_uuid(
        db: Session,
        uuid: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        icon: Optional[str] = None,
        is_active: Optional[bool] = None,
        enable_l0_retrieval: Optional[bool] = None,
        enable_l1_retrieval: Optional[bool] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        根据UUID更新角色信息（一个用户只有一个角色）
        如果角色不存在，则创建新角色（用于输入昵称时创建role记录）
        
        Args:
            db: 数据库会话
            uuid: 角色UUID（对应loads.id）
            name: 角色名称（可选，创建时必填）
            description: 描述（可选）
            system_prompt: 系统提示词（可选）
            icon: 图标（可选）
            is_active: 是否激活（可选）
            enable_l0_retrieval: 是否启用L0检索（可选）
            enable_l1_retrieval: 是否启用L1检索（可选）
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            role = db.query(Role).filter(Role.uuid == uuid).first()
            
            # 如果角色不存在，创建新角色
            if not role:
                # 创建角色时需要name
                if not name or not name.strip():
                    return False, f"创建角色时name不能为空"
                
                # 获取loads信息以获取loads.name（用于生成system_prompt）
                from app.models.load import Load
                load = db.query(Load).filter(Load.id == uuid).first()
                if not load:
                    return False, f"未找到ID为 {uuid} 的用户"
                
                # 创建新角色，id = uuid = loads.id
                # 注意：此时不生成system_prompt，等到信息采集完成时才生成
                role, role_error, role_status = RoleService.create_role(
                    db=db,
                    uuid=uuid,
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
                    return False, f"创建角色失败: {role_error}"
                
                # 创建成功后，刷新role对象
                role = db.query(Role).filter(Role.uuid == uuid).first()
                if not role:
                    return False, "创建角色后无法找到角色记录"
                
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
                    logger.info(f"成功创建并更新UUID为 {uuid} 的角色信息")
                    return True, None
                else:
                    logger.info(f"成功创建UUID为 {uuid} 的角色")
                    return True, None
            
            # 更新角色信息（角色已存在的情况）
            if name is not None:
                # 检查名称是否与其他角色冲突（排除当前角色）
                existing_role = db.query(Role).filter(
                    Role.name == name.strip(),
                    Role.uuid != role.uuid
                ).first()
                if existing_role:
                    return False, f"角色名称 {name} 已被其他角色使用"
                
                role.name = name.strip()
                
                # 创建l1_versions和l1_bios的初始记录（如果不存在）
                # 这个方法内部会检查是否已存在，避免重复创建
                success_l1, error_l1 = L1BioService.create_initial_l1_version_and_bio(
                    db=db,
                    role_id=role.uuid
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
            logger.info(f"成功更新UUID为 {uuid} 的角色信息")
            return True, None
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"数据库完整性错误: {str(e)}", exc_info=True)
            return False, "更新角色失败：数据完整性错误"
        except Exception as e:
            db.rollback()
            logger.error(f"更新角色信息失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def submit_info_collection(
        db: Session,
        uuid: str,
        description: str,
        system_prompt: str,
        content: Optional[str] = None,
        content_third_view: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        提交信息采集数据：更新roles和l1_bios表
        
        Args:
            db: 数据库会话
            uuid: 角色UUID（对应loads.id）
            description: 描述（职业和喜好）
            system_prompt: 系统提示词（由前端生成）
            content: 用户最近在做什么（存入l1_bios.content）
            content_third_view: AI生成的性格评价和MBTI（存入l1_bios.content_third_view）
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            # 获取角色信息
            role = db.query(Role).filter(Role.uuid == uuid).first()
            if not role:
                return False, f"未找到UUID为 {uuid} 的角色"
            
            # 更新roles表（description和system_prompt）
            success_role, error_role = RoleService.update_role_by_uuid(
                db=db,
                uuid=uuid,
                description=description if description else None,
                system_prompt=system_prompt
            )
            
            if not success_role:
                return False, f"更新roles表失败: {error_role}"
            
            # 重新查询role以确保获取最新的信息
            role = db.query(Role).filter(Role.uuid == uuid).first()
            if not role:
                return False, f"更新后无法找到UUID为 {uuid} 的角色"
            
            # 确保创建l1_versions和l1_bios记录（如果不存在）
            # 注意：l1_bios.role_id 和 l1_versions.role_id 使用 roles.uuid（varchar(64)），不是 roles.id（varchar(36)）
            from sqlalchemy import text
            
            # 检查是否存在该角色的l1_bios记录
            result = db.execute(
                text("""
                    SELECT id, version 
                    FROM l1_bios 
                    WHERE role_id = :role_id
                    ORDER BY version DESC
                    LIMIT 1
                """),
                {"role_id": role.uuid}
            ).fetchone()
            
            if not result:
                # 记录不存在，需要先创建l1_versions和l1_bios记录
                success_l1, error_l1 = L1BioService.create_initial_l1_version_and_bio(
                    db=db,
                    role_id=role.uuid
                )
                if not success_l1:
                    logger.warning(f"创建l1_versions和l1_bios失败: {error_l1}")
                    # 不返回错误，继续执行
            
            # 更新l1_bios表（content和content_third_view）
            if content is not None or content_third_view is not None:
                update_fields = []
                params = {"role_id": role.uuid}
                
                if content is not None:
                    update_fields.append("content = :content")
                    params["content"] = content
                
                if content_third_view is not None:
                    update_fields.append("content_third_view = :content_third_view")
                    params["content_third_view"] = content_third_view
                
                if update_fields:
                    db.execute(
                        text(f"""
                            UPDATE l1_bios 
                            SET {', '.join(update_fields)}
                            WHERE role_id = :role_id
                            AND version = (
                                SELECT MAX(version) 
                                FROM l1_bios 
                                WHERE role_id = :role_id
                            )
                        """),
                        params
                    )
                    logger.info(f"Updated l1_bios for role_id={role.uuid}")
            
            db.commit()
            
            logger.info(f"成功提交信息采集数据: uuid={uuid}")
            return True, None
        except Exception as e:
            db.rollback()
            logger.error(f"提交信息采集数据失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def generate_system_prompt(
        db: Session,
        uuid: str
    ) -> Tuple[bool, Optional[str]]:
        """
        根据角色的description生成system_prompt并更新到roles表
        注意：此方法使用role.description，如果role.description为空，则从loads.description获取
        
        Args:
            db: 数据库会话
            uuid: 角色UUID（对应loads.id）
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            # 获取角色信息
            role = db.query(Role).filter(Role.uuid == uuid).first()
            if not role:
                return False, f"未找到UUID为 {uuid} 的角色"
            
            # 获取用户信息（用于生成system_prompt中的loads.name）
            from app.models.load import Load
            load = db.query(Load).filter(Load.id == uuid).first()
            if not load:
                return False, f"未找到ID为 {uuid} 的用户"
            
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
            success_role, error_role = RoleService.update_role_by_uuid(
                db=db,
                uuid=uuid,
                system_prompt=system_prompt
            )
            
            if not success_role:
                return False, f"更新system_prompt失败: {error_role}"
            
            logger.info(f"成功为用户 {uuid} 生成并更新system_prompt")
            return True, None
        except Exception as e:
            db.rollback()
            logger.error(f"生成system_prompt失败: {str(e)}", exc_info=True)
            return False, str(e)
    

