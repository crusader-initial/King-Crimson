from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

# Mask password for logging
masked_url = settings.DATABASE_URL.replace(settings.POSTGRES_PASSWORD, "******")
logging.info(f"Connecting to PostgreSQL database at: {masked_url}")

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # 验证连接是否有效
    pool_size=5,  # 连接池大小
    max_overflow=10  # 最大溢出连接数
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
