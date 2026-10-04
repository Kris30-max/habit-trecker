import pytest
from pydantic import ValidationError

from bot.config import Settings


def make(**kwargs: object) -> Settings:
    return Settings(_env_file=None, bot_token="123:abc", **kwargs)


def test_allowed_ids_parsed_from_comma_string() -> None:
    assert make(allowed_user_ids="1, 2,3,").allowed_user_ids == frozenset({1, 2, 3})


def test_empty_database_url_is_none() -> None:
    assert make(database_url="").database_url is None


def test_invalid_timezone_rejected() -> None:
    with pytest.raises(ValidationError):
        make(default_tz="Mars/Olympus")
