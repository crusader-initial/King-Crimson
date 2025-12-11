from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

# Mask password for logging
masked_url = settings.DATABASE_URL.replace(settings.MYSQL_PASSWORD, "******")
print(f"Connecting to database at: {masked_url}")
print(f"Using password: {settings.MYSQL_PASSWORD}")  # Temporary debug

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
