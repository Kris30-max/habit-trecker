from aiogram import Dispatcher
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.handlers import get_root_router
from bot.middlewares.access import AccessMiddleware
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.user import UserMiddleware


def build_dispatcher(
    session_factory: async_sessionmaker[AsyncSession],
    allowed_user_ids: frozenset[int],
    default_tz: str,
) -> Dispatcher:
    dp = Dispatcher()
    # Порядок важен: сначала whitelist, потом сессия БД, потом пользователь
    dp.update.outer_middleware(AccessMiddleware(allowed_user_ids))
    dp.update.outer_middleware(DbSessionMiddleware(session_factory))
    dp.update.outer_middleware(UserMiddleware(default_tz))
    dp.include_router(get_root_router())
    return dp
