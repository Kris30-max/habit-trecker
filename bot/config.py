from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: SecretStr
    allowed_user_ids: Annotated[frozenset[int], NoDecode] = frozenset()
    database_url: SecretStr
    default_tz: str = "Europe/Moscow"
    tick_seconds: int = 60
    log_level: str = "INFO"

    @field_validator("allowed_user_ids", mode="before")
    @classmethod
    def _parse_ids(cls, value: object) -> object:
        if isinstance(value, str):
            return frozenset(int(part) for part in value.split(",") if part.strip())
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def _use_asyncpg(cls, value: object) -> object:
        # Supabase отдаёт строку вида postgresql://… — приводим к async-драйверу
        if isinstance(value, str):
            for prefix in ("postgresql://", "postgres://"):
                if value.startswith(prefix):
                    return "postgresql+asyncpg://" + value.removeprefix(prefix)
        return value

    @field_validator("default_tz")
    @classmethod
    def _check_tz(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Unknown timezone: {value}") from exc
        return value
