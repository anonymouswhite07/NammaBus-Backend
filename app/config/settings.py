from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API Settings
    PROJECT_NAME: str = "Namma Bus API"
    API_V1_STR: str = "/api/v1"
    
    # Security Settings
    SECRET_KEY: str = "38a531bdfd70dc264a7ef19602a8bf3dcfcd3f9ad72a392ce818c39db5c54b2d"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database Settings
    DATABASE_URL: str = "sqlite+aiosqlite:///namma_bus.db"
    
    # Redis Cache Settings
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Firebase configuration
    FIREBASE_CREDENTIALS_PATH: str = "firebase-credentials.json"
    
    # CORS Origins
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
