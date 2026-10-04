from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User
from bot.handlers.formatting import stats_text
from bot.services.schedule import local_today
from bot.services.stats import build_stats

router = Router(name="stats")


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession, user: User) -> None:
    today = local_today(user.timezone)
    stats = await build_stats(session, user.id, user.timezone, today)
    await message.answer(stats_text(stats))
