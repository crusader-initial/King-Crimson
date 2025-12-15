from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Second-Me-Lite"
    
    # Database (PostgreSQL with PGVector)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres123"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "second_me_lite"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Embedding 配置
    EMBEDDING_DIMENSION: int = 1024  # multimodal-embedding-v1 的维度

    # LLM (Remote API - 百炼)
    DASHSCOPE_API_KEY: str
    OPENAI_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    CHAT_MODEL: str = "qwen3-vl-32b-thinking"
    EMBEDDING_MODEL: str = "multimodal-embedding-v1"

    class Config:
        env_file = ".env"

settings = Settings()

# 调试：打印实际使用的配置值
print("=" * 50)
print("DEBUG: 配置加载信息")
print("=" * 50)
print(f"OPENAI_BASE_URL: {settings.OPENAI_BASE_URL}")
print(f"CHAT_MODEL: {settings.CHAT_MODEL}")
print(f"EMBEDDING_MODEL: {settings.EMBEDDING_MODEL}")
print(f"DASHSCOPE_API_KEY (前10位): {settings.DASHSCOPE_API_KEY[:10]}..." if settings.DASHSCOPE_API_KEY else "DASHSCOPE_API_KEY: 未设置")
print("=" * 50)
