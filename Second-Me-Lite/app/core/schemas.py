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

