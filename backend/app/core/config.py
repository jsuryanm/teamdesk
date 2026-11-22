from functools import lru_cache
from typing import Literal, Self
# Self refers instance of class 

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
    environment: Literal["local", "test", "production", "staging"] = 'local'

    database_url: str = "postgresql+psycopg://teamdesk:teamdesk@localhost:5432/teamdesk"
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=10, ge=0, le=100)

    secret_key: SecretStr = SecretStr(INSECURE_DEFAULT_KEY)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(60, ge=1, le=1440)
    cors_origins: list[str] = ["http://localhost:8501"]

    logfire_token: SecretStr | None = None 

    @model_validator(mode='after')
    def _forbid_insecure_in_production(self) -> Self:
        """Checks for valid key during the staging and production"""
        if self.environment in {'staging', 'production'}:
            key = self.secret_key.get_secret_value()
            if key == INSECURE_DEFAULT_KEY or len(key) < 32:
                raise ValueError("SECRET_KEY must be send to a random value")
        return self

@lru_cache
def get_settings() -> Settings:
    """Cached so we parse the environment once. Used as a FastAPI dependency too."""
    return Settings()