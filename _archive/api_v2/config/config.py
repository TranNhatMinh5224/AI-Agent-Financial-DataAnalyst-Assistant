from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@127.0.0.1:5432/vifinqa"
    
    # Vector DB
    QDRANT_URL: str = "http://127.0.0.1:6333"
    
    # Redis (Window Context)
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    
    # MinIO
    MINIO_URL: str = "http://127.0.0.1:9000"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "password123"
    MINIO_BUCKET_NAME: str = "vifinqa-documents"
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Financial Analyst API"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
