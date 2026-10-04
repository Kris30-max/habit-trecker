import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.config import Settings
from bot.db.session import create_engine, create_session_factory
from bot.dispatcher import build_dispatcher

logger = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command="today", description="Привычки на сегодня"),
    BotCommand(command="add", description="Добавить привычку"),
    BotCommand(command="list", description="Все привычки"),
    BotCommand(command="delete", description="Убрать привычку в архив"),
    BotCommand(command="cancel", description="Отменить действие"),
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
    dp = build_dispatcher(session_factory, settings.allowed_user_ids, settings.default_tz)

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
