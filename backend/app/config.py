from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: Optional[str] = None
    
    # Redis (for later)
    REDIS_URL: Optional[str] = None
    
    # ML/AI (for later)
    GEMINI_API_KEY: Optional[str] = None
    
    # Railway
    PORT: int = 8000
    RAILWAY_ENVIRONMENT: Optional[str] = "development"
    
    # Application
    APP_NAME: str = "Hockey Analytics API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()