from pydantic_settings import BaseSettings
from pathlib import Path

# 获取项目根目录（Second-Me-Lite/）
# 当前文件在 app/core/config.py，所以需要向上两级
_project_root = Path(__file__).parent.parent.parent
_env_file = _project_root / ".env"

class Settings(BaseSettings):
    PROJECT_NAME: str = "Second-Me-Lite"
    
    # Database (PostgreSQL with PGVector) - 必须从 .env 配置
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # LLM (Remote API - 自部署模型) - 必须从 .env 配置
    CHAT_API_KEY: str
    OPENAI_BASE_URL: str
    CHAT_MODEL: str

    # Embedding 配置（使用 HuggingFace BAAI/bge-m3 本地模型）
    EMBEDDING_DIMENSION: int = 1024  # bge-m3 的维度，可通过 .env 覆盖
    EMBEDDING_MODEL: str = "BAAI/bge-m3"  # HuggingFace 模型名称，可通过 .env 覆盖

    # Document Chunking 配置
    DOCUMENT_CHUNK_SIZE: int = 500  # 文档分块大小，可通过 .env 覆盖
    DOCUMENT_CHUNK_OVERLAP: int = 50  # 文档分块重叠大小，可通过 .env 覆盖
    PREFER_LANGUAGE: str = "zh_CN"  # 偏好语言，可通过 .env 覆盖

    class Config:
        env_file = str(_env_file)  # 使用绝对路径指向项目根目录的 .env 文件
        env_file_encoding = 'utf-8'  # 明确指定 UTF-8 编码

settings = Settings()


class Config:
    """配置类，提供 from_env() 方法和 get() 方法以兼容旧代码"""
    
    def __init__(self, settings: Settings):
        self._settings = settings
    
    @classmethod
    def from_env(cls):
        """从环境变量加载配置"""
        return cls(settings)
    
    def get(self, key: str, default=None):
        """获取配置值"""
        return getattr(self._settings, key, default)

# 调试：打印实际使用的配置值
print("=" * 50)
print("DEBUG: 配置加载信息")
print("=" * 50)
print(f"POSTGRES_HOST: {settings.POSTGRES_HOST}")
print(f"POSTGRES_PORT: {settings.POSTGRES_PORT}")
print(f"POSTGRES_DB: {settings.POSTGRES_DB}")
print(f"POSTGRES_USER: {settings.POSTGRES_USER}")
print(f"OPENAI_BASE_URL: {settings.OPENAI_BASE_URL}")
print(f"CHAT_MODEL: {settings.CHAT_MODEL}")
print(f"CHAT_API_KEY (前10位): {settings.CHAT_API_KEY[:10]}..." if settings.CHAT_API_KEY else "CHAT_API_KEY: 未设置")
print(f"EMBEDDING_MODEL: {settings.EMBEDDING_MODEL}")
print(f"EMBEDDING_DIMENSION: {settings.EMBEDDING_DIMENSION}")
print("=" * 50)
