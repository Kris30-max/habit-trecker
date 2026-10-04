import pytest
from pydantic import ValidationError

from bot.config import Settings


def make(**kwargs: object) -> Settings:
    kwargs.setdefault("database_url", "sqlite+aiosqlite://")
    return Settings(_env_file=None, bot_token="123:abc", **kwargs)


def test_allowed_ids_parsed_from_comma_string() -> None:
    assert make(allowed_user_ids="1, 2,3,").allowed_user_ids == frozenset({1, 2, 3})


@pytest.mark.parametrize("prefix", ["postgresql://", "postgres://"])
def test_supabase_url_switched_to_asyncpg(prefix: str) -> None:
    url = make(database_url=f"{prefix}u:p@host:5432/db").database_url.get_secret_value()
    assert url == "postgresql+asyncpg://u:p@host:5432/db"


def test_invalid_timezone_rejected() -> None:
    with pytest.raises(ValidationError):
        make(default_tz="Mars/Olympus")
