from functools import lru_cache
from typing import Literal, Self

from pydantic import SecretStr, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


INSECURE_DEFAULT_KEY = "dev-only-insecure-secret-key-change-me-0123456789"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    app_name: str = "TeamDesk API"
    app_version: str = "1.0.0"
    environment: Literal["local", "test", "production", "staging"]

    database_url: str = "postgresql+psycopg://teamdesk:teamdesk@localhost:5432/teamdesk"
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=10, ge=0, le=100)

    