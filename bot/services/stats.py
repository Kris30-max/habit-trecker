from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Habit
from bot.db.repositories import habits as habits_repo
from bot.services.schedule import to_local_date
from bot.services.streaks import (
    Completion,
    DayMark,
    best_streak,
    completion,
    current_streak,
    last_days,
)


@dataclass(frozen=True)
class HabitStats:
    habit: Habit
    current: int
    best: int
    week: Completion
    month: Completion
    last7: list[DayMark]


async def build_stats(
    session: AsyncSession, user_id: int, tz: str, today: date
) -> list[HabitStats]:
    habits = await habits_repo.list_active(session, user_id)
    logs = await habits_repo.logs_by_habit(session, [h.id for h in habits])
    result = []
    for habit in habits:
        created = to_local_date(habit.created_at, tz)
        habit_logs = logs[habit.id]
        mask = habit.schedule_days
        result.append(
            HabitStats(
                habit=habit,
                current=current_streak(mask, created, habit_logs, today),
                best=best_streak(mask, created, habit_logs, today),
                week=completion(mask, created, habit_logs, today, 7),
                month=completion(mask, created, habit_logs, today, 30),
                last7=last_days(mask, created, habit_logs, today),
            )
        )
    return result


async def habit_streak(session: AsyncSession, habit: Habit, tz: str, today: date) -> int:
    logs = await habits_repo.logs_by_habit(session, [habit.id])
    created = to_local_date(habit.created_at, tz)
    return current_streak(habit.schedule_days, created, logs[habit.id], today)
