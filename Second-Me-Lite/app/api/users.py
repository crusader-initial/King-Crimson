from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.services.load_service import LoadService
from app.services.role_service import RoleService
from app.core.response import APIResponse
from app.core.schemas import LoginRequest, UpdateLoadRequest, UpdateDescriptionRequest, UpdateRoleRequest, InfoCollectionRequest, InfoCollectionLLMRequest
from app.core.config import settings
from openai import OpenAI
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/loads/login")
def login_or_create_load(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    登录或创建用户接口（根据手机号）
    如果用户存在，返回用户ID；不存在则创建并返回用户ID
    
    请求体示例:
    {
        "user_mobile": "13800138000",
        "name": "用户名"  // 可选，创建新用户时使用
    }
    """
    try:
        load, error, status_code, is_new_user = LoadService.get_or_create_load_by_mobile(
            db=db,
            user_mobile=request.user_mobile,
            name=request.name
        )
        
        if error:
            return APIResponse.error(code=status_code, message=error)
        
        return APIResponse.success(
            data={
                'id': load.id,
                'user_mobile': load.user_mobile,
                'name': load.name,
                'is_new_user': is_new_user  # 标识是否是新用户
            },
            message="登录成功" if not is_new_user else "用户创建成功"
        )
    except Exception as e:
        logger.error("登录或创建用户失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")

@router.get("/loads/{load_id}")
def get_load_by_id(
    load_id: str,
    db: Session = Depends(get_db)
):
    """
    根据用户ID获取用户信息
    
    Args:
        load_id: 用户ID
    """
    try:
        load, error, status_code = LoadService.get_load_by_id(
            db=db,
            load_id=load_id
        )
        
        if error:
            return APIResponse.error(code=status_code, message=error)
        
        return APIResponse.success(
            data=load.to_dict(),
            message="获取用户信息成功"
        )
    except Exception as e:
        logger.error("获取用户信息失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")

@router.put("/loads/{load_id}")
def update_load(
    load_id: str,
    request: UpdateLoadRequest,
    db: Session = Depends(get_db)
):
    """
    根据用户ID更新用户信息（支持更新整条记录）
    
    请求体示例:
    {
        "name": "新用户名",
        "description": "新描述",
        "email": "new@example.com"
        // 其他字段可选
    }
    """
    try:
        success, error = LoadService.update_load_by_id(
            db=db,
            load_id=load_id,
            name=request.name,
            description=request.description,
            email=request.email,
            avatar_data=request.avatar_data,
            instance_id=request.instance_id,
            instance_password=request.instance_password,
            status=request.status
        )
        if not success:
            return APIResponse.error(code=400, message=error)
        return APIResponse.success(message="用户信息更新成功")
    except Exception as e:
        logger.error("更新用户信息失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")

@router.post("/loads/description")
def update_description(
    request: UpdateDescriptionRequest,
    load_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """
    更新用户描述（不更新system_prompt）
    从请求头 X-User-ID 获取用户ID
    
    请求体示例:
    {
        "description": "新描述"
    }
    """
    try:
        if not load_id:
            return APIResponse.error(code=400, message="缺少用户ID（X-User-ID请求头）")
        
        success, error = LoadService.update_description_only(
            db=db,
            load_id=load_id,
            description=request.description
        )
        if not success:
            return APIResponse.error(code=400, message=error)
        return APIResponse.success(message="描述更新成功")
    except Exception as e:
        logger.error("更新用户描述失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")

@router.post("/loads/generate-system-prompt")
def generate_system_prompt(
    load_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """
    根据用户的description生成system_prompt并更新到roles表
    从请求头 X-User-ID 获取用户ID
    """
    try:
        if not load_id:
            return APIResponse.error(code=400, message="缺少用户ID（X-User-ID请求头）")
        
        success, error = RoleService.generate_system_prompt(
            db=db,
            uuid=load_id
        )
        if not success:
            return APIResponse.error(code=400, message=error)
        return APIResponse.success(message="system_prompt生成成功")
    except Exception as e:
        logger.error("生成system_prompt失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")

@router.get("/roles/{uuid}")
def get_role_by_uuid(
    uuid: str,
    db: Session = Depends(get_db)
):
    """
    根据UUID获取角色信息
    
    Args:
        uuid: 角色UUID（对应loads.id）
    """
    try:
        role, error, status_code = RoleService.get_role_by_uuid(
            db=db,
            uuid=uuid
        )
        
        if error:
            return APIResponse.error(code=status_code, message=error)
        
        return APIResponse.success(
            data=role.to_dict(),
            message="获取角色信息成功"
        )
    except Exception as e:
        logger.error("获取角色信息失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")

@router.put("/roles/{uuid}")
def update_role(
    uuid: str,
    request: UpdateRoleRequest,
    db: Session = Depends(get_db)
):
    """
    根据UUID更新角色信息（支持更新整条记录，只设置需要更新的字段）
    
    请求体示例:
    {
        "name": "新角色名称",
        "description": "新描述",
        "system_prompt": "新系统提示词"
        // 其他字段可选
    }
    """
    try:
        success, error = RoleService.update_role_by_uuid(
            db=db,
            uuid=uuid,
            name=request.name,
            description=request.description,
            system_prompt=request.system_prompt,
            icon=request.icon,
            is_active=request.is_active,
            enable_l0_retrieval=request.enable_l0_retrieval,
            enable_l1_retrieval=request.enable_l1_retrieval
        )
        if not success:
            return APIResponse.error(code=400, message=error)
        return APIResponse.success(message="角色信息更新成功")
    except Exception as e:
        logger.error("更新角色信息失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")

@router.post("/info-collection/submit")
def submit_info_collection(
    request: InfoCollectionRequest,
    load_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """
    提交信息采集数据
    从请求头 X-User-ID 获取用户ID（loads.id）
    
    请求体示例:
    {
        "description": "职业：程序员；喜好：阅读",
        "content": "最近在做一个新项目",
        "content_third_view": "原来"我"喜欢这些呀--阅读\n嗯，如果要猜的话，我觉得"我"的性格类型也许是ISFP--艺术家型。\n这是"我"的模样"
    }
    """
    try:
        if not load_id:
            return APIResponse.error(code=400, message="缺少用户ID（X-User-ID请求头）")
        
        success, error = RoleService.submit_info_collection(
            db=db,
            uuid=load_id,
            description=request.description,
            system_prompt=request.system_prompt,
            content=request.content,
            content_third_view=request.content_third_view
        )
        if not success:
            return APIResponse.error(code=400, message=error)
        return APIResponse.success(message="信息采集数据提交成功")
    except Exception as e:
        logger.error("提交信息采集数据失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")

@router.post("/info-collection/llm")
def info_collection_llm(
    request: InfoCollectionLLMRequest,
    db: Session = Depends(get_db)
):
    """
    信息采集过程中的LLM调用接口
    不依赖role和system_prompt，直接调用OpenAI客户端
    """
    try:
        # 构建简单的消息，不依赖role和system_prompt
        messages = [
            {
                "role": "system",
                "content": "你现在是一个引导用户塑造\"第二自我\"的AI助手。你的任务是帮助用户通过对话来创建他们的AI角色。"
            },
            {
                "role": "user",
                "content": request.query
            }
        ]
        
        # 直接创建OpenAI客户端并调用，不经过chat_service
        client = OpenAI(
            api_key=settings.CHAT_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        
        # 直接调用LLM API
        response = client.chat.completions.create(
            model=settings.CHAT_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            stream=False
        )
        
        # 提取回答内容
        answer = ""
        if response.choices and len(response.choices) > 0:
            answer = response.choices[0].message.content if response.choices[0].message.content else ""
        
        return APIResponse.success(
            data={"answer": answer},
            message="LLM调用成功"
        )
    except Exception as e:
        logger.error("信息采集LLM调用失败!", exc_info=True)
        return APIResponse.error(code=500, message=f"Internal server error: {str(e)}")

