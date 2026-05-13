"""
Application configuration and settings.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/mathbattle"

    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "MathBattle"
    PROJECT_VERSION: str = "1.0.0"

    # JWT Configuration
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7

    # Email Configuration
    SENDGRID_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "noreply@mathbattle.com"
    EMAIL_FROM_NAME: str = "MathBattle"

    # Security
    BCRYPT_ROUNDS: int = 12

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    REGISTRATION_RATE_LIMIT: str = "5/hour"  # 5 registration attempts per hour

    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000", "http://localhost:8081", "http://192.168.0.102:8081"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
