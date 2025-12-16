from fastapi import FastAPI
from app.api.endpoints import router
from app.core.database import engine, Base
from app.core.config import settings
# 导入所有模型以确保表被创建
from app.models import Document, Chunk, ChatHistory, Load

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to Second-Me-Lite"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
