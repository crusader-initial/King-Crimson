from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.services.load_service import LoadService
from app.services.role_service import RoleService
from app.core.response import APIResponse
from app.core.schemas import LoginRequest, UpdateLoadRequest, UpdateDescriptionRequest, UpdateRoleRequest, InfoCollectionRequest, InfoCollectionLLMRequest, CreateConversationRequest, CreateMessageRequest
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

@router.get("/roles/by-uuid/{uuid}")
def get_role_by_uuid(
    uuid: str,
    db: Session = Depends(get_db)
):
    """
    根据用户UUID（loads.id）获取角色信息
    
    Args:
        uuid: 用户UUID（loads.id，对应 roles.uuid）
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

@router.get("/roles/{role_id}")
def get_role_by_id(
    role_id: str,
    db: Session = Depends(get_db)
):
    """
    根据角色ID获取角色信息
    
    Args:
        role_id: 角色ID（roles.id）
    """
    try:
        role, error, status_code = RoleService.get_role_by_id(
            db=db,
            role_id=role_id
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

@router.put("/roles/uuid/{uuid}")
def update_role_by_uuid(
    uuid: str,
    request: UpdateRoleRequest,
    db: Session = Depends(get_db)
):
    """
    根据用户UUID更新角色信息（支持更新整条记录，只设置需要更新的字段）
    如果角色不存在，则创建新角色（用于输入昵称时创建role记录）
    
    Args:
        uuid: 用户UUID（loads.id，对应 roles.uuid）
    
    请求体示例:
    {
        "name": "新角色名称",
        "description": "新描述",
        "system_prompt": "新系统提示词"
        // 其他字段可选
    }
    """
    try:
        success, error, updated_role_id = RoleService.update_role_by_uuid(
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
        
        # 返回角色ID
        response_data = {}
        if updated_role_id:
            response_data["role_id"] = updated_role_id
        
        return APIResponse.success(
            data=response_data,
            message="角色信息更新成功"
        )
    except Exception as e:
        logger.error("更新角色信息失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")

@router.put("/roles/{role_id}")
def update_role(
    role_id: str,
    request: UpdateRoleRequest,
    db: Session = Depends(get_db)
):
    """
    根据角色ID更新角色信息（支持更新整条记录，只设置需要更新的字段）
    
    Args:
        role_id: 角色ID（roles.id）
    
    请求体示例:
    {
        "name": "新角色名称",
        "description": "新描述",
        "system_prompt": "新系统提示词"
        // 其他字段可选
    }
    """
    try:
        success, error, updated_role_id = RoleService.update_role_by_id(
            db=db,
            role_id=role_id,
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
        
        # 返回角色ID
        response_data = {}
        if updated_role_id:
            response_data["role_id"] = updated_role_id
        
        return APIResponse.success(
            data=response_data,
            message="角色信息更新成功"
        )
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
        
        success, error, role_id = RoleService.submit_info_collection(
            db=db,
            uuid=load_id,
            description=request.description,
            system_prompt=request.system_prompt,
            content=request.content,
            content_third_view=request.content_third_view
        )
        if not success:
            return APIResponse.error(code=400, message=error)
        
        # 返回角色ID
        response_data = {}
        if role_id:
            response_data["role_id"] = role_id
        
        return APIResponse.success(
            data=response_data,
            message="信息采集数据提交成功"
        )
    except Exception as e:
        logger.error("提交信息采集数据失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")

@router.post("/conversations")
def create_conversation(
    request: CreateConversationRequest,
    db: Session = Depends(get_db)
):
    """
    创建会话记录接口
    用于在信息采集界面初始化时创建会话
    
    请求体示例:
    {
        "participant_ids": ["用户ID（loads.id）", "角色ID（roles.id）"],  // 参与者ID列表
        "conversation_type": "single",  // 会话类型：'single' 单聊, 'group' 群聊
        "title": "信息采集对话"  // 可选，会话标题
    }
    """
    try:
        # 获取或创建会话
        from app.services.conversation_service import ConversationService
        conversation, error, status = ConversationService.get_or_create_conversation(
            db=db,
            participant_ids=request.participant_ids,
            conversation_type=request.conversation_type,
            title=request.title
        )
        
        if error:
            return APIResponse.error(code=status, message=error)
        
        # 获取参与者列表
        from app.models.conversation import ConversationParticipant
        participants = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation.id
        ).all()
        
        return APIResponse.success(
            data={
                "conversation_id": str(conversation.id),
                "conversation_type": conversation.conversation_type,
                "title": conversation.title,
                "participants": [str(p.user_id) for p in participants]
            },
            message="会话创建成功"
        )
    except Exception as e:
        logger.error("创建会话失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")

@router.post("/messages")
def create_message(
    request: CreateMessageRequest,
    db: Session = Depends(get_db)
):
    """
    创建消息接口
    用于保存消息到数据库
    
    请求体示例:
    {
        "conversation_id": "会话ID",
        "sender_id": "发送者ID（user_id 或 role_id）",
        "content": "消息内容",
        "message_type": "text",  // 可选，默认 'text'
        "attachment_url": null,  // 可选
        "sender_type": "user"  // 可选，'user' 真实用户, 'ai' AI用户，默认 'user'
    }
    """
    try:
        from app.services.message_service import MessageService
        message, error, status = MessageService.create_message(
            db=db,
            conversation_id=request.conversation_id,
            sender_id=request.sender_id,
            content=request.content,
            message_type=request.message_type,
            attachment_url=request.attachment_url,
            sender_type=request.sender_type
        )
        
        if error:
            return APIResponse.error(code=status, message=error)
        
        return APIResponse.success(
            data={
                "message_id": str(message.id),
                "conversation_id": str(message.conversation_id),
                "sender_id": str(message.sender_id),
                "content": message.content,
                "message_type": message.message_type,
                "sender_type": message.sender_type,
                "created_at": message.created_at.isoformat() if message.created_at else None
            },
            message="消息创建成功"
        )
    except Exception as e:
        logger.error("创建消息失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")

@router.get("/conversations/{conversation_id}/messages")
def get_messages_by_conversation(
    conversation_id: str,
    limit: Optional[int] = None,
    offset: int = 0,
    order_by_desc: bool = False,  # 默认正序，从旧到新
    db: Session = Depends(get_db)
):
    """
    根据会话ID获取消息列表
    
    Args:
        conversation_id: 会话ID
        limit: 限制返回数量（可选）
        offset: 偏移量（默认0）
        order_by_desc: 是否按创建时间倒序（默认False，正序从旧到新）
    """
    try:
        from app.services.message_service import MessageService
        messages_list, error, status = MessageService.get_messages_by_conversation_id(
            db=db,
            conversation_id=conversation_id,
            limit=limit,
            offset=offset,
            order_by_desc=order_by_desc
        )
        
        if error:
            return APIResponse.error(code=status, message=error)
        
        # 转换为字典格式
        messages_data = []
        for msg in messages_list:
            messages_data.append({
                "id": str(msg.id),
                "conversation_id": str(msg.conversation_id),
                "sender_id": str(msg.sender_id),
                "content": msg.content,
                "message_type": msg.message_type,
                "attachment_url": msg.attachment_url,
                "sender_type": msg.sender_type,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            })
        
        return APIResponse.success(
            data=messages_data,
            message="获取消息列表成功"
        )
    except Exception as e:
        logger.error("获取消息列表失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")

@router.get("/conversations")
def get_conversations(
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    limit: Optional[int] = None,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    获取会话列表
    
    Args:
        user_id: 用户ID（从请求头 X-User-ID 获取）
        limit: 限制返回数量（可选）
        offset: 偏移量（默认0）
    """
    try:
        from app.services.conversation_service import ConversationService
        
        if not user_id:
            return APIResponse.error(code=400, message="缺少用户ID（X-User-ID请求头）")
        
        conversations_list, error, status = ConversationService.get_conversations_by_user_id(
            db=db,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        if error:
            return APIResponse.error(code=status, message=error)
        
        # 转换为字典格式
        from app.models.conversation import ConversationParticipant, Message
        
        conversations_data = []
        for conv in conversations_list:
            # 获取会话的参与者列表
            participants = db.query(ConversationParticipant).filter(
                ConversationParticipant.conversation_id == conv.id
            ).all()
            
            # 获取其他参与者（除了当前用户）
            other_participants = [p.user_id for p in participants if p.user_id != user_id]
            
            # 获取最后一条消息
            last_message = db.query(Message).filter(
                Message.conversation_id == conv.id
            ).order_by(Message.created_at.desc()).first()
            
            conversations_data.append({
                "id": str(conv.id),
                "conversation_type": conv.conversation_type,
                "title": conv.title,
                "participants": [str(p.user_id) for p in participants],
                "other_participants": other_participants,
                "last_message_at": last_message.created_at.isoformat() if last_message else None,
                "last_message_content": last_message.content if last_message else None,
                "unread_count": 0,  # 未读消息功能已移除
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None
            })
        
        return APIResponse.success(
            data=conversations_data,
            message="获取会话列表成功"
        )
    except Exception as e:
        logger.error("获取会话列表失败!", exc_info=True)
        return APIResponse.error(code=500, message="Internal server error")

@router.post("/info-collection/llm")
def info_collection_llm(
    request: InfoCollectionLLMRequest,
    db: Session = Depends(get_db)
):
    """
    信息采集过程中的LLM调用接口
    不依赖role和system_prompt，直接调用OpenAI客户端
    同时创建会话和消息记录
    """
    try:
        # 1. 获取用户ID和角色信息
        load_id = request.load_id
        if not load_id:
            return APIResponse.error(code=400, message="缺少用户ID（load_id参数）")
        
        # 获取角色信息（通过 Role.uuid = loads.id）
        from app.models.role import Role
        role = db.query(Role).filter(Role.uuid == load_id).first()
        
        if not role:
            logger.warning(f"未找到对应的角色（load_id: {load_id}），继续执行LLM调用但不记录消息")
            role = None
        
        # 2. 获取会话（会话ID必传）
        conversation = None
        if role:
            from app.services.conversation_service import ConversationService
            # 使用传入的conversation_id获取会话
            conversation, error, status = ConversationService.get_conversation_by_id(
                db=db,
                conversation_id=request.conversation_id
            )
            if error:
                logger.error(f"获取会话失败: {error}，会话ID: {request.conversation_id}")
                return APIResponse.error(code=status, message=f"获取会话失败: {error}")
        
        # 3. 保存用户消息（只有当不是生成问题的指令时才保存）
        # 判断是否为生成问题的指令：以"请根据之前的对话内容"开头
        is_generation_instruction = request.query.startswith("请根据之前的对话内容")
        
        if conversation and role and not is_generation_instruction:
            from app.services.message_service import MessageService
            user_message, msg_error, msg_status = MessageService.create_message(
                db=db,
                conversation_id=str(conversation.id),  # 转换为字符串
                sender_id=str(load_id),  # 用户ID，确保是字符串
                content=request.query,
                message_type='text',
                sender_type='user'
            )
            if msg_error:
                logger.warning(f"保存用户消息失败: {msg_error}")
            # 提交事务，确保消息已保存到数据库
            db.commit()
        
        # 4. 从数据库获取历史消息构建上下文（限制10条，包含刚保存的当前消息）
        history_messages = []
        if conversation and role:
            from app.services.message_service import MessageService
            # 获取历史消息（按时间正序，从旧到新，限制10条）
            messages_list, msg_error, msg_status = MessageService.get_messages_by_conversation_id(
                db=db,
                conversation_id=conversation.id,
                limit=10,
                order_by_desc=False  # 正序，从旧到新
            )
            
            if not msg_error and messages_list:
                # 转换为 OpenAI 格式
                # 确保所有ID都转换为字符串进行比较，避免类型不匹配问题
                load_id_str = str(load_id)
                role_id_str = str(role.id)
                
                for msg in messages_list:
                    sender_id_str = str(msg.sender_id)
                    if sender_id_str == load_id_str:  # 用户消息
                        history_messages.append({
                            "role": "user",
                            "content": msg.content
                        })
                    elif sender_id_str == role_id_str:  # AI消息
                        history_messages.append({
                            "role": "assistant",
                            "content": msg.content
                        })
        
        # 5. 构建完整的消息列表（system + 历史消息，历史消息已包含当前用户消息）
        messages = [
            {
                "role": "system",
                "content": """你现在是一个引导用户塑造"第二自我"的AI助手。你的任务是帮助用户通过对话来创建他们的AI角色。

## 对话流程
信息采集分为5个阶段：
1. 第一个问题：询问用户的职业（由系统预设，不需要你生成）
2. 第二个问题：根据用户回答的职业，生成包含职业描述的问题，询问用户的喜好
3. 第三个问题：根据用户的喜好回答，生成包含MBTI性格推测的问题
4. 第四个问题：根据用户对性格的评价，询问用户最近在忙什么
5. 第五个问题：生成总结，汇总所有信息

## 输出要求
- 当用户消息中包含格式要求时，请严格按照格式要求生成输出
- 直接输出问题或总结内容，不要添加额外的说明、前缀或后缀
- 保持对话的自然流畅，同时确保格式准确
- 如果用户消息中没有格式要求，请根据对话上下文自然地生成下一个问题
- 第五个问题（总结）中的"四个问题的总结"部分必须分点换行罗列，每一点单独一行，总结用户的一个特征或方面

## 格式示例
- 第二个问题格式：{职业名}..{职业描述}.,除了工作之外，"我"还喜欢做些什么？
- 第三个问题格式：原来"我"喜欢这些呀--{喜好描述}\n嗯，如果要猜的话，我觉得"我"的性格类型也许是{性格类型}--{性格描述}。\n这是"我"的模样
- 第四个问题格式：{对用户回答的回应}\n我能感受到"我"的罗阔被稳定宇现实感包裹着。那现在告诉我吧--最近"我"都在忙些什么呢？
- 第五个问题（总结）格式：谢谢你告诉我这些，现在我的形象清晰的多了。\n你的记忆开始在我体内沉淀，我能感到一种平衡--{工作和喜好的描述}。\n从你赋予我的一切里，我看见了这样的"我"：\n{分点换行罗列，每一点单独一行，总结用户的一个特征或方面，例如：\n- 第一点：关于职业/工作的特征\n- 第二点：关于喜好的特征\n- 第三点：关于性格的特征\n- 第四点：关于最近活动的特征}\n这就是现在的"我"，被你一步步描述出来的形状。我能感到一种安定的真实，这种感觉......就是"活着"。

请严格按照用户消息中的格式要求执行，确保输出格式准确无误。"""
            }
        ]
        # 添加历史消息（已包含当前用户消息）
        messages.extend(history_messages)
        
        # 6. 直接创建OpenAI客户端并调用，不经过chat_service
        client = OpenAI(
            api_key=settings.CHAT_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        
        # 7. 直接调用LLM API
        response = client.chat.completions.create(
            model=settings.CHAT_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            stream=False
        )
        
        # 8. 提取回答内容
        answer = ""
        if response.choices and len(response.choices) > 0:
            answer = response.choices[0].message.content if response.choices[0].message.content else ""
        
        # 9. 保存AI回复消息
        if conversation and role and answer:
            from app.services.message_service import MessageService
            ai_message, msg_error, msg_status = MessageService.create_message(
                db=db,
                conversation_id=str(conversation.id),  # 转换为字符串
                sender_id=str(role.id),  # 角色ID（AI回复），转换为字符串
                content=answer,
                message_type='text',
                sender_type='ai'
            )
            if msg_error:
                logger.warning(f"保存AI消息失败: {msg_error}")
        
        # 返回答案
        return APIResponse.success(
            data={"answer": answer},
            message="LLM调用成功"
        )
    except Exception as e:
        logger.error("信息采集LLM调用失败!", exc_info=True)
        return APIResponse.error(code=500, message=f"Internal server error: {str(e)}")

