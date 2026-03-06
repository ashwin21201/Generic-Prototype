"""Pydantic settings for the configurator. Load from .env in backend directory."""
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
import json
import os


def _backend_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    APP_NAME: str = "Intent-Based Architecture Configurator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    DATABASE_URL_ASYNC: str = "sqlite+aiosqlite:///./configurator.db"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: Optional[str] = "http://localhost:5173,http://localhost:3000"
    LOG_LEVEL: str = "INFO"
    LLM_PROVIDER: str = "claude"
    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    USE_AI_INFERENCE: bool = True
    INFERENCE_CONFIDENCE_THRESHOLD: float = 0.7

    @property
    def cors_origins_list(self) -> List[str]:
        v = self.CORS_ORIGINS or ""
        if isinstance(v, list):
            return v
        if v.strip().startswith("["):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        return [x.strip() for x in v.split(",") if x.strip()] or ["*"]

    class Config:
        env_file = os.path.join(_backend_dir(), ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
