import os
from typing import Optional

class Settings:
    """
    Application settings and configuration
    """
    API_TITLE: str = "Your API"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    
    CORS_ORIGINS: list = ["*"]  # Configure for production

settings = Settings()