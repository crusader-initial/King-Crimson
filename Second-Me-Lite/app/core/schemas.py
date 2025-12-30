from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class SimpleChatRequest(BaseModel):
    """简单的聊天请求格式（用于前端兼容）"""
    query: str  # 用户查询

class ChatRequest(BaseModel):
    """Chat request in OpenAI-compatible format"""
    # Core OpenAI API fields
    messages: List[Dict[str, str]]  # OpenAI compatible messages array
    model: Optional[str] = None  # Model identifier
    temperature: float = 0.1  # Temperature parameter for controlling randomness
    max_tokens: int = 2000  # Maximum tokens to generate
    stream: bool = True  # Whether to stream response
    
    # Metadata for request processing - contains extension parameters
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)  # Additional parameters for LLM request processing

class LoginRequest(BaseModel):
    """登录请求模型（根据手机号获取或创建用户）"""
    user_mobile: str
    name: Optional[str] = None  # 可选，创建新用户时使用

class UpdateLoadRequest(BaseModel):
    """更新用户请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    email: Optional[str] = None
    avatar_data: Optional[str] = None
    instance_id: Optional[str] = None
    instance_password: Optional[str] = None
    status: Optional[str] = None

class UpdateDescriptionRequest(BaseModel):
    """更新用户描述请求模型（不更新system_prompt）"""
    description: str

class UpdateRoleRequest(BaseModel):
    """更新角色请求模型（支持更新整条记录）"""
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None
    enable_l0_retrieval: Optional[bool] = None
    enable_l1_retrieval: Optional[bool] = None

class InfoCollectionLLMRequest(BaseModel):
    """信息采集LLM请求模型（用于信息采集过程中的LLM调用）"""
    query: str  # 用户查询或上下文
    load_id: str  # 用户ID（loads.id）

class InfoCollectionRequest(BaseModel):
    """信息采集提交请求模型"""
    description: str
    system_prompt: str  # 前端生成的system_prompt
    content: Optional[str] = None
    content_third_view: Optional[str] = None

class StatusBiographyRequest(BaseModel):
    """状态传记请求模型（用于创建或更新）"""
    content: Optional[str] = None
    content_third_view: Optional[str] = None
    summary: Optional[str] = None
    summary_third_view: Optional[str] = None

class L1BioRequest(BaseModel):
    """L1传记请求模型"""
    content_third_view: str

# 文档分析相关模型
class FileInfo(BaseModel):
    """文件信息"""
    data_type: str  # mime_type
    filename: str
    content: str  # raw_content
    file_content: Optional[Dict[str, Any]] = None

class BioInfo(BaseModel):
    """用户传记信息"""
    global_bio: str = ""
    status_bio: str = ""
    about_me: str = ""

class InsighterInput(BaseModel):
    """Insight 生成输入"""
    file_info: FileInfo
    bio_info: BioInfo

class SummarizerInput(BaseModel):
    """Summary 生成输入"""
    file_info: FileInfo
    insight: str  # 已生成的 insight（Overview + Breakdown 格式化后的文本）

class AnalyzeDocumentRequest(BaseModel):
    """文档分析请求模型"""
    document_id: int  # 文档ID

class GenerateStatusBioRequest(BaseModel):
    """生成状态传记请求模型"""
    role_id: str  # 角色ID，用于获取该角色的所有文档并生成状态传记

class GenerateL1Request(BaseModel):
    """生成L1数据请求模型"""
    role_id: str  # 角色ID，用于获取该角色的所有文档并生成L1数据

class CreateConversationRequest(BaseModel):
    """创建会话请求模型"""
    user_id: str  # 用户ID（loads.id）
    participant_id: str  # 参与者ID（roles.id 或其他用户ID）
    participant_type: str  # 参与者类型（必传，如 'role'）
    title: Optional[str] = None  # 会话标题（可选）

class CreateMessageRequest(BaseModel):
    """创建消息请求模型"""
    conversation_id: str  # 会话ID
    sender_id: str  # 发送者ID（user_id 或 role_id）
    receiver_id: str  # 接收者ID（user_id 或 role_id）
    content: str  # 消息内容
    message_type: str = 'text'  # 消息类型（默认 'text'）
    attachment_url: Optional[str] = None  # 附件URL（可选）

class AdvancedChatRequest(BaseModel):
    """高级聊天请求模型 - 多阶段迭代优化"""
    requirement: str = Field(..., description="用户的大致需求")
    max_iterations: int = Field(default=3, ge=1, le=10, description="最大迭代优化次数")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="模型生成温度")
    enable_l0_retrieval: bool = Field(default=True, description="是否启用L0知识检索")
    enable_l1_retrieval: bool = Field(default=True, description="是否启用L1知识检索")
    role_id: Optional[str] = Field(default=None, description="角色ID，用于系统定制和知识检索")
    model: Optional[str] = Field(default=None, description="模型标识符")
    max_tokens: int = Field(default=2000, ge=100, le=8000, description="最大生成token数")


class ValidationResult(BaseModel):
    """验证结果模型"""
    is_valid: bool = Field(..., description="验证是否通过")
    feedback: str = Field(default="", description="验证反馈信息")


class AdvancedChatResponse(BaseModel):
    """高级聊天响应模型"""
    enhanced_requirement: str = Field(..., description="增强后的需求")
    solution: str = Field(..., description="生成的解决方案")
    validation_history: List[ValidationResult] = Field(default_factory=list, description="验证历史")
    final_format: Optional[str] = Field(default=None, description="最终格式化的解决方案")
    final_response: Optional[Any] = Field(default=None, description="最终响应（支持流式）")
    iterations_used: int = Field(..., description="实际使用的迭代次数")

