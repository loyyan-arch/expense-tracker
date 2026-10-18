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

    # HTTP 本地开发需显式设为 false；公网 HTTPS 保持 true。
    session_cookie_secure: bool = True
    browser_origins: list[str] = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:18080", "http://127.0.0.1:18080",
    ]

    @field_validator("database_path")
    @classmethod
    def resolve_database_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            value = BASE_DIR / value
        return value.resolve()


settings = Settings()
