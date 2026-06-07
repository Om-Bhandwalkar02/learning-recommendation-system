"""
Core Configuration Module
Loads and validates all environment variables using Pydantic Settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List
from pathlib import Path

# Always resolve .env relative to this file's location (project root)
ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings with environment variable loading."""

    # App metadata
    APP_NAME: str = "Learning Recommendation System"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-powered course recommendation engine"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Dataset
    DATASET_PATH: str = "data/courses.csv"

    # Groq AI
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5500,http://127.0.0.1:5500"

    # Recommendation Engine
    MIN_RECOMMENDATION_SCORE: float = 0.05
    MAX_RECOMMENDATIONS: int = 20
    DEFAULT_RECOMMENDATIONS: int = 10

    @property
    def cors_origins(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def groq_enabled(self) -> bool:
        """Check if Groq API is configured."""
        return bool(self.GROQ_API_KEY and self.GROQ_API_KEY != "your_groq_api_key_here")

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance - loaded once at startup."""
    return Settings()
