from collections.abc import Sequence
from datetime import date, time

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Habit, HabitLog, HabitStatus


async def create(
    session: AsyncSession,
    user_id: int,
    title: str,
    schedule_days: int,
    remind_time: time | None,
) -> Habit:
    habit = Habit(
        user_id=user_id, title=title, schedule_days=schedule_days, remind_time=remind_time
    )
    session.add(habit)
    await session.flush()
    return habit


async def list_active(session: AsyncSession, user_id: int) -> Sequence[Habit]:
    result = await session.scalars(
        select(Habit)
        .where(Habit.user_id == user_id, Habit.is_archived.is_(False))
        .order_by(Habit.created_at, Habit.id)
    )
    return result.all()


async def get_owned(session: AsyncSession, habit_id: int, user_id: int) -> Habit | None:
    """Привычка пользователя или None — защита от чужих habit_id в callback."""
    return await session.scalar(select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id))


async def statuses_for_day(
    session: AsyncSession, habit_ids: Sequence[int], day: date
) -> dict[int, HabitStatus]:
    if not habit_ids:
        return {}
    rows = await session.execute(
        select(HabitLog.habit_id, HabitLog.status).where(
            HabitLog.habit_id.in_(habit_ids), HabitLog.date == day
        )
    )
    return {habit_id: HabitStatus(status) for habit_id, status in rows}


async def logs_by_habit(
    session: AsyncSession, habit_ids: Sequence[int]
) -> dict[int, dict[date, HabitStatus]]:
    """Вся история отметок по привычкам: {habit_id: {дата: статус}}."""
    result: dict[int, dict[date, HabitStatus]] = {habit_id: {} for habit_id in habit_ids}
    if not habit_ids:
        return result
    rows = await session.execute(
        select(HabitLog.habit_id, HabitLog.date, HabitLog.status).where(
            HabitLog.habit_id.in_(habit_ids)
        )
    )
    for habit_id, day, status in rows:
        result[habit_id][day] = HabitStatus(status)
    return result


async def set_status(
    session: AsyncSession, habit_id: int, day: date, status: HabitStatus | None
) -> None:
    """Ставит отметку за день; None — снимает её."""
    if status is None:
        await session.execute(
            delete(HabitLog).where(HabitLog.habit_id == habit_id, HabitLog.date == day)
        )
        return
    log = await session.scalar(
        select(HabitLog).where(HabitLog.habit_id == habit_id, HabitLog.date == day)
    )
    if log is None:
        session.add(HabitLog(habit_id=habit_id, date=day, status=status))
    else:
        log.status = status
    await session.flush()
