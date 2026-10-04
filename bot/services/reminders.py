"""Когда что отправлять — чистые функции для тикера (TECH_SPEC.md, раздел 6)."""

from datetime import UTC, date, datetime, time, timedelta

from bot.db.models import Habit
from bot.services.schedule import is_scheduled

# Окно догоняющей отправки: если бот лежал, напоминание уйдёт, когда он поднимется,
# но не позже чем через 2 часа после назначенного времени.
CATCH_UP = timedelta(hours=2)
SNOOZE = timedelta(hours=1)


def moment_today(at: time, now_local: datetime) -> datetime:
    return datetime.combine(now_local.date(), at, tzinfo=now_local.tzinfo)


def in_window(at: time | None, now_local: datetime) -> bool:
    if at is None:
        return False
    moment = moment_today(at, now_local)
    return moment <= now_local < moment + CATCH_UP


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def reminder_due(habit: Habit, now_local: datetime) -> bool:
    """Пора ли слать плановое напоминание (без учёта отметок — их проверяет тикер)."""
    today: date = now_local.date()
    if habit.is_archived or habit.remind_time is None:
        return False
    if habit.last_reminded_on == today or not is_scheduled(habit.schedule_days, today):
        return False
    if not in_window(habit.remind_time, now_local):
        return False
    # Привычку завели уже после сегодняшнего времени напоминания — сегодня не дёргаем
    return _aware(habit.created_at) <= moment_today(habit.remind_time, now_local)


def summary_due(
    summary_time: time | None, last_summary_on: date | None, now_local: datetime
) -> bool:
    return last_summary_on != now_local.date() and in_window(summary_time, now_local)
