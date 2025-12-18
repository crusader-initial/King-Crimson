from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Tuple, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class L1BioService:
    """L1传记服务"""
    
    @staticmethod
    def create_new_version(db: Session, role_id: str, content_third_view: str) -> Tuple[bool, Optional[str]]:
        """
        创建新的L1传记记录（新版本，按角色ID）
        
        Args:
            db: 数据库会话
            role_id: 角色UUID（roles.uuid，String类型，对应loads.id）
            content_third_view: 新的第三方视角内容
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            # 获取该角色的当前最大版本号
            max_version_result = db.execute(
                text("""
                    SELECT COALESCE(MAX(version), 0) as max_version 
                    FROM l1_bios 
                    WHERE role_id = :role_id
                """),
                {"role_id": role_id}
            ).fetchone()
            next_version = (max_version_result[0] if max_version_result else 0) + 1
            
            # 创建新记录
            db.execute(
                text("""
                    INSERT INTO l1_bios (role_id, version, content_third_view) 
                    VALUES (:role_id, :version, :content_third_view)
                """),
                {"role_id": role_id, "version": next_version, "content_third_view": content_third_view}
            )
            
            db.commit()
            logger.info(f"Created new l1_bios record for role_id={role_id} with version {next_version}")
            return True, None
        except Exception as e:
            db.rollback()
            logger.error(f"创建L1传记失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def update_by_role_id(
        db: Session,
        role_id: str,
        content_third_view: str
    ) -> Tuple[bool, Optional[str]]:
        """
        创建或更新L1传记记录（按角色ID，upsert）
        
        Args:
            db: 数据库会话
            role_id: 角色UUID（roles.uuid，String类型，对应loads.id）
            content_third_view: 新的第三方视角内容
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            # 检查是否存在该角色的记录
            result = db.execute(
                text("""
                    SELECT id, version 
                    FROM l1_bios 
                    WHERE role_id = :role_id
                    ORDER BY version DESC
                    LIMIT 1
                """),
                {"role_id": role_id}
            ).fetchone()
            
            if result:
                # 记录存在，更新最新版本
                db.execute(
                    text("""
                        UPDATE l1_bios 
                        SET content_third_view = :content_third_view
                        WHERE role_id = :role_id
                        AND version = (
                            SELECT MAX(version) 
                            FROM l1_bios 
                            WHERE role_id = :role_id
                        )
                    """),
                    {"role_id": role_id, "content_third_view": content_third_view}
                )
                logger.info(f"Updated l1_bios.content_third_view for role_id={role_id}")
            else:
                # 记录不存在，创建新记录（版本从1开始）
                db.execute(
                    text("""
                        INSERT INTO l1_bios (role_id, version, content_third_view) 
                        VALUES (:role_id, 1, :content_third_view)
                    """),
                    {"role_id": role_id, "content_third_view": content_third_view}
                )
                logger.info(f"Created new l1_bios record for role_id={role_id}, version=1")
            
            db.commit()
            return True, None
        except Exception as e:
            db.rollback()
            logger.error(f"保存L1传记失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def update_latest_version(db: Session, content_third_view: str) -> Tuple[bool, Optional[str]]:
        """
        更新最新的L1传记记录（兼容旧接口，已废弃，建议使用 update_by_role_id）
        
        Args:
            db: 数据库会话
            content_third_view: 新的第三方视角内容
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        logger.warning("update_latest_version 方法已废弃，建议使用 update_by_role_id")
        try:
            # 检查是否存在记录
            result = db.execute(
                text("""
                    SELECT id, version 
                    FROM l1_bios 
                    WHERE version = (
                        SELECT MAX(version) FROM l1_bios
                    )
                    LIMIT 1
                """)
            ).fetchone()
            
            if not result:
                return False, "未找到L1传记记录，请先创建"
            
            # 更新最新记录
            db.execute(
                text("""
                    UPDATE l1_bios 
                    SET content_third_view = :content_third_view
                    WHERE version = (
                        SELECT MAX(version) FROM l1_bios
                    )
                """),
                {"content_third_view": content_third_view}
            )
            
            db.commit()
            logger.info("Updated latest l1_bios.content_third_view")
            return True, None
        except Exception as e:
            db.rollback()
            logger.error(f"更新L1传记失败: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def update_content_third_view(db: Session, content_third_view: str) -> Tuple[bool, Optional[str]]:
        """
        更新L1传记第三方视角内容（兼容旧接口，内部调用 update_latest_version）
        
        Args:
            db: 数据库会话
            content_third_view: 新的第三方视角内容
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        return L1BioService.update_latest_version(db, content_third_view)
    
    @staticmethod
    def get_latest_content_third_view(db: Session) -> Optional[str]:
        """
        获取最新的L1传记第三方视角内容
        
        Args:
            db: 数据库会话
            
        Returns:
            内容字符串，如果不存在返回None
        """
        try:
            result_query = db.execute(
                text("""
                    SELECT content_third_view 
                    FROM l1_bios 
                    WHERE version = (
                        SELECT MAX(version) FROM l1_bios
                    )
                    LIMIT 1
                """)
            ).fetchone()
            
            return result_query[0] if result_query else None
        except Exception as e:
            logger.warning(f"获取l1_bios.content_third_view失败: {str(e)}")
            return None
    
    @staticmethod
    def create_initial_l1_version_and_bio(
        db: Session,
        role_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        为角色创建初始的l1_versions和l1_bios记录
        
        Args:
            db: 数据库会话
            role_id: 角色UUID（roles.uuid，String类型，varchar(64)，对应loads.id）
                    注意：l1_bios.role_id 和 l1_versions.role_id 使用 roles.uuid，不是 roles.id
            
        Returns:
            Tuple[是否成功, 错误信息]
        """
        try:
            # 检查是否已经存在该角色的l1_versions记录
            existing_version = db.execute(
                text("""
                    SELECT version 
                    FROM l1_versions 
                    WHERE role_id = :role_id
                    LIMIT 1
                """),
                {"role_id": role_id}
            ).fetchone()
            
            if existing_version:
                logger.info(f"角色 {role_id} 的l1_versions记录已存在，跳过创建")
                return True, None
            
            # 获取全局最大的version号，确保version是全局唯一的
            max_version_result = db.execute(
                text("""
                    SELECT COALESCE(MAX(version), 0) as max_version 
                    FROM l1_versions
                """)
            ).fetchone()
            version = (max_version_result[0] if max_version_result else 0) + 1
            
            status = 'active'
            description = '初始版本'
            create_time = datetime.utcnow()
            
            db.execute(
                text("""
                    INSERT INTO l1_versions (version, create_time, status, description, role_id)
                    VALUES (:version, :create_time, :status, :description, :role_id)
                """),
                {
                    "version": version,
                    "create_time": create_time,
                    "status": status,
                    "description": description,
                    "role_id": role_id
                }
            )
            
            # 创建l1_bios记录
            db.execute(
                text("""
                    INSERT INTO l1_bios (version, content, content_third_view, summary, summary_third_view, create_time, role_id)
                    VALUES (:version, :content, :content_third_view, :summary, :summary_third_view, :create_time, :role_id)
                """),
                {
                    "version": version,
                    "content": None,
                    "content_third_view": None,
                    "summary": None,
                    "summary_third_view": None,
                    "create_time": create_time,
                    "role_id": role_id
                }
            )
            
            db.commit()
            logger.info(f"成功为角色 {role_id} 创建初始l1_versions和l1_bios记录")
            return True, None
        except Exception as e:
            db.rollback()
            logger.error(f"创建初始l1_versions和l1_bios记录失败: {str(e)}", exc_info=True)
            return False, str(e)

