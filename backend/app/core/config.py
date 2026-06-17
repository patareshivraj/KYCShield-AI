import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "KYCShield AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # SQLite Configuration
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./kycshield.db"
    
    # Storage Configuration
    STORAGE_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage")
    
    # File Limits
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_MIME_TYPES: list[str] = ["image/jpeg", "image/png", "application/pdf"]
    MAX_PDF_PAGES: int = 20
    
    class Config:
        case_sensitive = True

settings = Settings()

# Ensure storage directories exist
os.makedirs(os.path.join(settings.STORAGE_DIR, "source"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "normalized"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "evidence"), exist_ok=True)
