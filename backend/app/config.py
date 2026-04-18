"""Pydantic settings for PrenatalAI."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATA_DIR: str = "/data"
    CHROMA_PATH: str = "/data/vector_db"
    DB_PATH: str = "/data/db.sqlite"

    # Ollama settings (for Dev1's medgemma module)
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "medgemma"

    # Image storage
    IMAGE_DIR: str = "/data/images"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
