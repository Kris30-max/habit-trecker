"""Чистые функции подсчёта серий и статистики — без БД, легко тестировать.

Правила (TECH_SPEC.md, 5.2–5.3):
- незапланированный день серию не прерывает;
- сегодня без отметки серию не прерывает (день ещё не закончился);
- «пропущено» или прошедший день без отметки — прерывает.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from bot.db.models import HabitStatus
from bot.services.schedule import is_scheduled

Logs = Mapping[date, HabitStatus]


class DayMark(StrEnum):
    DONE = "done"
    SKIPPED = "skipped"
    MISSED = "missed"
    PENDING = "pending"  # сегодня, ещё не отмечено
    OFF = "off"  # не запланировано или до создания привычки


@dataclass(frozen=True)
class Completion:
    done: int
    planned: int

    @property
    def percent(self) -> int | None:
        return round(self.done * 100 / self.planned) if self.planned else None


def _days(start: date, end: date) -> Iterator[date]:
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def history_start(created: date, logs: Logs) -> date:
    """Начало истории: дата создания или более ранняя отметка («вчера» в день создания)."""
    return min(created, *logs) if logs else created


def day_mark(schedule_days: int, start: date, logs: Logs, day: date, today: date) -> DayMark:
    status = logs.get(day)
    if status == HabitStatus.DONE:
        return DayMark.DONE
    if status == HabitStatus.SKIPPED:
        return DayMark.SKIPPED
    if day < start or day > today or not is_scheduled(schedule_days, day):
        return DayMark.OFF
    return DayMark.PENDING if day == today else DayMark.MISSED


def current_streak(schedule_days: int, created: date, logs: Logs, today: date) -> int:
    start = history_start(created, logs)
    streak = 0
    day = today
    while day >= start:
        mark = day_mark(schedule_days, start, logs, day, today)
        if mark == DayMark.DONE:
            streak += 1
        elif mark in (DayMark.SKIPPED, DayMark.MISSED):
            break
        day -= timedelta(days=1)
    return streak


def best_streak(schedule_days: int, created: date, logs: Logs, today: date) -> int:
    start = history_start(created, logs)
    best = run = 0
    for day in _days(start, today):
        mark = day_mark(schedule_days, start, logs, day, today)
        if mark == DayMark.DONE:
            run += 1
            best = max(best, run)
        elif mark in (DayMark.SKIPPED, DayMark.MISSED):
            run = 0
    return best


def completion(
    schedule_days: int, created: date, logs: Logs, today: date, window: int
) -> Completion:
    """Доля выполненных запланированных дней за последние `window` дней.

    Сегодняшний день учитывается, только если по нему уже есть отметка.
    """
    start = max(today - timedelta(days=window - 1), history_start(created, logs))
    done = planned = 0
    for day in _days(start, today):
        mark = day_mark(schedule_days, start, logs, day, today)
        if mark in (DayMark.OFF, DayMark.PENDING):
            continue
        planned += 1
        done += mark == DayMark.DONE
    return Completion(done=done, planned=planned)


def last_days(
    schedule_days: int, created: date, logs: Logs, today: date, count: int = 7
) -> list[DayMark]:
    start = history_start(created, logs)
    return [
        day_mark(schedule_days, start, logs, today - timedelta(days=offset), today)
        for offset in range(count - 1, -1, -1)
    ]
