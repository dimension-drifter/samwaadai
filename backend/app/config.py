from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    DATABASE_URL: str = "sqlite:///./call_tracker.db"
    
    # API Keys
    GEMINI_API_KEY: Optional[str] = None
    ASSEMBLYAI_API_KEY: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None
    
    # Email Configuration
    SENDER_EMAIL: str = "pkmpunit2003@gmail.com"
    
    # Google Calendar Configuration
    GOOGLE_CREDENTIALS_PATH: str = "credentials.json"
    GOOGLE_TOKEN_PATH: str = "token.json"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Allow extra fields from .env (remove strict validation)
        extra = "ignore"  # Changed from "forbid" to "ignore"

settings = Settings()