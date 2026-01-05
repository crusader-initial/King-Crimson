"""
项目启动脚本
在项目根目录运行此脚本，确保工作目录正确
"""
from fastapi import FastAPI
from app.core.database import engine, Base
from app.core.config import settings
# 导入所有模型以确保表被创建
from app.models import Document, Chunk, Load, StatusBiography, Role
from app.models.l1 import L1Version, L1Bio, L1Shade, L1Cluster, L1ChunkTopic

# 导入所有路由
from app.api import health, chat, files, users, biography, kernel

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

# 注册所有路由
app.include_router(health.router, prefix="/api", tags=["健康检查"])
app.include_router(chat.router, prefix="/api", tags=["聊天"])
app.include_router(files.router, prefix="/api", tags=["文件管理"])
app.include_router(users.router, prefix="/api", tags=["用户管理"])
app.include_router(biography.router, prefix="/api", tags=["传记管理"])
app.include_router(kernel.router, prefix="/api/kernel", tags=["内核服务"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Second-Me-Lite"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "run:app",  # 使用模块字符串以支持 reload 功能
        host="0.0.0.0",  # 允许其他电脑访问（前端默认连接本地 localhost）
        port=8001,
        reload=True
    )

