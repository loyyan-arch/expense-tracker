from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="forbid",
        hide_input_in_errors=True,
    )

    jwt_secret: SecretStr = Field(min_length=32)

    access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
    )

    database_path: Path = BASE_DIR / "expenses.db"

    @field_validator("database_path")
    @classmethod
    def resolve_database_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            value = BASE_DIR / value
        return value.resolve()


settings = Settings()