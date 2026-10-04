from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories import users


class UserMiddleware(BaseMiddleware):
    """Находит или регистрирует пользователя и кладёт его в data["user"]."""

    def __init__(self, default_tz: str) -> None:
        self.default_tz = default_tz

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        if tg_user is not None:
            session: AsyncSession = data["session"]
            data["user"] = await users.get_or_create(
                session, tg_user.id, tg_user.first_name, self.default_tz
            )
        return await handler(event, data)
