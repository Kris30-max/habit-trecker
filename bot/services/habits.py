from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Habit, HabitStatus
from bot.db.repositories import habits as habits_repo
from bot.services.schedule import is_scheduled

TITLE_MAX_LEN = 64


@dataclass(frozen=True)
class DayItem:
    habit: Habit
    status: HabitStatus | None


def clean_title(text: str | None) -> str | None:
    """Обрезает пробелы; None, если название пустое или слишком длинное."""
    title = " ".join((text or "").split())
    if not title or len(title) > TITLE_MAX_LEN:
        return None
    return title


async def day_items(session: AsyncSession, user_id: int, day: date) -> list[DayItem]:
    """Привычки, запланированные на день, с их отметками."""
    habits = [
        h
        for h in await habits_repo.list_active(session, user_id)
        if is_scheduled(h.schedule_days, day)
    ]
    statuses = await habits_repo.statuses_for_day(session, [h.id for h in habits], day)
    return [DayItem(habit=h, status=statuses.get(h.id)) for h in habits]
