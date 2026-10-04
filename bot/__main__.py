import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.config import Settings
from bot.db.session import create_engine, create_session_factory
from bot.handlers import get_root_router
from bot.middlewares.access import AccessMiddleware
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.user import UserMiddleware

logger = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command="start", description="Начать работу"),
    BotCommand(command="help", description="Справка"),
]


async def main() -> None:
    settings = Settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    engine = create_engine(settings.database_url.get_secret_value())
    session_factory = create_session_factory(engine)

    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    # Порядок важен: сначала whitelist, потом сессия БД, потом пользователь
    dp.update.outer_middleware(AccessMiddleware(settings.allowed_user_ids))
    dp.update.outer_middleware(DbSessionMiddleware(session_factory))
    dp.update.outer_middleware(UserMiddleware(settings.default_tz))
    dp.include_router(get_root_router())

    await bot.set_my_commands(COMMANDS)
    await bot.delete_webhook()
    logger.info("Bot started, allowed users: %d", len(settings.allowed_user_ids))
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
