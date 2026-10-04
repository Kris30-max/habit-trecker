"""Запросы тикера. claim_* — условные UPDATE: возвращают True только тому,
кто первым «забрал» отправку, поэтому два инстанса не пришлют дубль."""

from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Habit, User


async def users_with_reminders(session: AsyncSession) -> Sequence[User]:
    result = await session.scalars(select(User).where(User.reminders_enabled.is_(True)))
    return result.all()


async def habits_with_reminders(session: AsyncSession, user_id: int) -> Sequence[Habit]:
    result = await session.scalars(
        select(Habit).where(
            Habit.user_id == user_id,
            Habit.is_archived.is_(False),
            or_(Habit.remind_time.is_not(None), Habit.snoozed_until.is_not(None)),
        )
    )
    return result.all()


async def claim_reminder(session: AsyncSession, habit_id: int, today: date) -> bool:
    result = await session.execute(
        update(Habit)
        .where(
            Habit.id == habit_id,
            or_(Habit.last_reminded_on.is_(None), Habit.last_reminded_on != today),
        )
        .values(last_reminded_on=today)
    )
    return result.rowcount == 1


async def claim_snooze(session: AsyncSession, habit_id: int, until: datetime) -> bool:
    result = await session.execute(
        update(Habit)
        .where(Habit.id == habit_id, Habit.snoozed_until == until)
        .values(snoozed_until=None)
    )
    return result.rowcount == 1


async def claim_summary(session: AsyncSession, user_id: int, today: date) -> bool:
    result = await session.execute(
        update(User)
        .where(
            User.id == user_id,
            or_(User.last_summary_on.is_(None), User.last_summary_on != today),
        )
        .values(last_summary_on=today)
    )
    return result.rowcount == 1


async def disable_reminders(session: AsyncSession, user_id: int) -> None:
    await session.execute(update(User).where(User.id == user_id).values(reminders_enabled=False))
