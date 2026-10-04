from typing import Any

from aiogram.types import User

from bot.middlewares.access import AccessMiddleware


async def _handler(event: Any, data: dict[str, Any]) -> str:
    return "handled"


def _user(user_id: int) -> User:
    return User(id=user_id, is_bot=False, first_name="Test")


async def test_allowed_user_passes() -> None:
    mw = AccessMiddleware(frozenset({1}))
    assert await mw(_handler, object(), {"event_from_user": _user(1)}) == "handled"


async def test_unknown_user_blocked() -> None:
    mw = AccessMiddleware(frozenset({1}))
    assert await mw(_handler, object(), {"event_from_user": _user(2)}) is None


async def test_update_without_user_blocked() -> None:
    mw = AccessMiddleware(frozenset({1}))
    assert await mw(_handler, object(), {}) is None
