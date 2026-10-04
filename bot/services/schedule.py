import re
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from bot.db.models import ALL_DAYS

WEEKDAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
WORKDAYS = 0b0011111
WEEKEND = 0b1100000

MONTHS_GENITIVE = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)

_TIME_RE = re.compile(r"^\s*(\d{1,2})(?:[:.\s](\d{2}))?\s*$")


def is_scheduled(schedule_days: int, day: date) -> bool:
    return bool(schedule_days & (1 << day.weekday()))


def toggle_day(schedule_days: int, weekday: int) -> int:
    return schedule_days ^ (1 << weekday)


def format_days(schedule_days: int) -> str:
    if schedule_days == ALL_DAYS:
        return "каждый день"
    if schedule_days == WORKDAYS:
        return "по будням"
    if schedule_days == WEEKEND:
        return "по выходным"
    return ", ".join(name for i, name in enumerate(WEEKDAYS) if schedule_days & (1 << i))


def format_date(day: date) -> str:
    return f"{day.day} {MONTHS_GENITIVE[day.month - 1]}"


def parse_time(text: str) -> time | None:
    """Разбирает «21:00», «9.30», «7 15», «8» в time; иначе None."""
    match = _TIME_RE.match(text)
    if match is None:
        return None
    hour, minute = int(match[1]), int(match[2] or 0)
    if hour > 23 or minute > 59:
        return None
    return time(hour, minute)


def local_now(tz: str, now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)).astimezone(ZoneInfo(tz))


def local_today(tz: str, now: datetime | None = None) -> date:
    return local_now(tz, now).date()


def can_mark(day: date, today: date) -> bool:
    """Отмечать можно сегодня и вчера (поздно нажал на вчерашнее напоминание)."""
    return today - timedelta(days=1) <= day <= today
