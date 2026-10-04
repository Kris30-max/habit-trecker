"""Тикер: раз в минуту рассылает напоминания, отложенные напоминания и вечерние сводки.

Состояния в памяти нет — всё читается из БД, поэтому рестарт ничего не теряет.
"""

import asyncio
import logging
import time
from datetime import UTC, date, datetime
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot import texts
from bot.db.models import Habit, User
from bot.db.repositories import habits as habits_repo
from bot.db.repositories import reminders as reminders_repo
from bot.handlers.formatting import day_text
from bot.keyboards.habits import day_keyboard, reminder_keyboard
from bot.services.habits import day_items
from bot.services.reminders import reminder_due, summary_due
from bot.services.schedule import local_now, plural_days
from bot.services.stats import habit_streak

logger = logging.getLogger(__name__)


class _Blocked(Exception):
    """Пользователь заблокировал бота — дальше ему не пишем."""


async def run_ticker(
    bot: Bot, session_factory: async_sessionmaker[AsyncSession], interval: int
) -> None:
    logger.info("Ticker started, interval=%ss", interval)
    while True:
        # Просыпаемся в начале минуты, чтобы напоминание в 10:00 ушло в 10:00, а не в 10:00:59
        await asyncio.sleep(interval - time.time() % interval + 1)
        try:
            await tick(bot, session_factory)
        except Exception:
            logger.exception("Tick failed")


async def tick(
    bot: Bot, session_factory: async_sessionmaker[AsyncSession], now: datetime | None = None
) -> None:
    now = now or datetime.now(UTC)
    async with session_factory() as session:
        users = await reminders_repo.users_with_reminders(session)
    for user in users:
        async with session_factory() as session:
            try:
                await _process_user(bot, session, user, now)
            except _Blocked:
                logger.warning("User %s blocked the bot, reminders disabled", user.telegram_id)
                await reminders_repo.disable_reminders(session, user.id)
                await session.commit()
            except Exception:
                logger.exception("Failed to process reminders for user %s", user.telegram_id)


async def _process_user(bot: Bot, session: AsyncSession, user: User, now: datetime) -> None:
    now_local = local_now(user.timezone, now)
    today = now_local.date()

    habits = await reminders_repo.habits_with_reminders(session, user.id)
    marked = await habits_repo.statuses_for_day(session, [h.id for h in habits], today)
    for habit in habits:
        if habit.id in marked:
            continue
        snoozed = habit.snoozed_until
        if snoozed is not None:
            aware = snoozed if snoozed.tzinfo else snoozed.replace(tzinfo=UTC)
            if aware <= now and await reminders_repo.claim_snooze(session, habit.id, snoozed):
                await session.commit()
                await _send_reminder(bot, session, user, habit, today)
            continue
        if reminder_due(habit, now_local) and await reminders_repo.claim_reminder(
            session, habit.id, today
        ):
            await session.commit()
            await _send_reminder(bot, session, user, habit, today)

    if summary_due(user.summary_time, user.last_summary_on, now_local):
        if not await reminders_repo.claim_summary(session, user.id, today):
            return
        await session.commit()
        items = await day_items(session, user.id, today)
        if items:
            text = texts.SUMMARY_HEADER + "\n\n" + day_text(items, today, today)
            await _send(bot, user, text, day_keyboard(items, today))


async def _send_reminder(
    bot: Bot, session: AsyncSession, user: User, habit: Habit, today: date
) -> None:
    lines = [texts.REMINDER.format(title=escape(habit.title))]
    streak = await habit_streak(session, habit, user.timezone, today)
    if streak:
        lines.append(texts.REMINDER_STREAK.format(days=plural_days(streak)))
    await _send(bot, user, "\n".join(lines), reminder_keyboard(habit.id, today))
    logger.info("Reminder sent: habit=%s user=%s", habit.id, user.telegram_id)


async def _send(bot: Bot, user: User, text: str, markup: InlineKeyboardMarkup) -> None:
    try:
        await bot.send_message(user.telegram_id, text, reply_markup=markup)
    except TelegramForbiddenError as exc:
        raise _Blocked from exc
    except TelegramAPIError:
        logger.exception("Failed to send message to user %s", user.telegram_id)
