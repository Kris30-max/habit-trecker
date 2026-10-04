from datetime import date, timedelta

import pytest

from bot.db.models import ALL_DAYS, HabitStatus
from bot.services.schedule import WORKDAYS, plural_days
from bot.services.streaks import (
    DayMark,
    best_streak,
    completion,
    current_streak,
    last_days,
)

D, S = HabitStatus.DONE, HabitStatus.SKIPPED
# Понедельник 5 октября 2026 … воскресенье 11 октября
MON = date(2026, 10, 5)


def day(offset: int) -> date:
    return MON + timedelta(days=offset)


def test_streak_counts_consecutive_done_days() -> None:
    logs = {day(0): D, day(1): D, day(2): D}
    assert current_streak(ALL_DAYS, day(0), logs, today=day(2)) == 3


def test_today_without_mark_does_not_break_streak() -> None:
    logs = {day(0): D, day(1): D}
    assert current_streak(ALL_DAYS, day(0), logs, today=day(2)) == 2


def test_missed_past_day_breaks_streak() -> None:
    logs = {day(0): D, day(2): D}
    assert current_streak(ALL_DAYS, day(0), logs, today=day(2)) == 1


def test_skipped_day_breaks_streak() -> None:
    logs = {day(0): D, day(1): S, day(2): D}
    assert current_streak(ALL_DAYS, day(0), logs, today=day(2)) == 1


def test_unscheduled_weekend_does_not_break_streak() -> None:
    # Пт выполнено, Сб/Вс не запланированы, Пн выполнено
    logs = {day(4): D, day(7): D}
    assert current_streak(WORKDAYS, day(4), logs, today=day(7)) == 2


def test_extra_done_on_unscheduled_day_counts() -> None:
    logs = {day(4): D, day(5): D}  # Пт и Сб при расписании «будни»
    assert current_streak(WORKDAYS, day(4), logs, today=day(5)) == 2


def test_new_habit_has_no_streak() -> None:
    assert current_streak(ALL_DAYS, day(0), {}, today=day(0)) == 0


def test_mark_for_yesterday_on_creation_day_counts() -> None:
    # Привычку создали сегодня, но отметили «вчера»
    logs = {day(0): D, day(1): D}
    assert current_streak(ALL_DAYS, day(1), logs, today=day(1)) == 2


def test_best_streak_finds_longest_run() -> None:
    logs = {day(0): D, day(1): D, day(2): D, day(4): D, day(5): D}
    assert best_streak(ALL_DAYS, day(0), logs, today=day(5)) == 3
    assert current_streak(ALL_DAYS, day(0), logs, today=day(5)) == 2


def test_completion_ignores_today_until_marked() -> None:
    logs = {day(0): D, day(1): S}
    result = completion(ALL_DAYS, day(0), logs, today=day(2), window=7)
    assert (result.done, result.planned, result.percent) == (1, 2, 50)


def test_completion_window_starts_at_creation() -> None:
    result = completion(ALL_DAYS, day(5), {day(5): D}, today=day(5), window=30)
    assert (result.done, result.planned) == (1, 1)


def test_completion_without_data() -> None:
    assert completion(ALL_DAYS, day(0), {}, today=day(0), window=7).percent is None


def test_last_days_marks() -> None:
    logs = {day(0): D, day(1): S, day(4): D}
    marks = last_days(WORKDAYS, day(0), logs, today=day(6), count=7)
    assert marks == [
        DayMark.DONE,  # Пн
        DayMark.SKIPPED,  # Вт
        DayMark.MISSED,  # Ср
        DayMark.MISSED,  # Чт
        DayMark.DONE,  # Пт
        DayMark.OFF,  # Сб
        DayMark.OFF,  # Вс (сегодня, не запланировано)
    ]


def test_last_days_before_creation_is_off() -> None:
    marks = last_days(ALL_DAYS, day(6), {}, today=day(6), count=3)
    assert marks == [DayMark.OFF, DayMark.OFF, DayMark.PENDING]


@pytest.mark.parametrize(
    ("n", "text"),
    [(1, "1 день"), (2, "2 дня"), (5, "5 дней"), (11, "11 дней"), (21, "21 день"), (24, "24 дня")],
)
def test_plural_days(n: int, text: str) -> None:
    assert plural_days(n) == text
