import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.config import Settings
from bot.handlers import get_root_router
from bot.middlewares.access import AccessMiddleware

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

    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.update.outer_middleware(AccessMiddleware(settings.allowed_user_ids))
    dp.include_router(get_root_router())

    await bot.set_my_commands(COMMANDS)
    await bot.delete_webhook()
    logger.info("Bot started, allowed users: %d", len(settings.allowed_user_ids))
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
