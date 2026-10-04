from datetime import UTC, date, datetime, time

import pytest

from bot.services.schedule import (
    WORKDAYS,
    can_mark,
    format_date,
    format_days,
    is_scheduled,
    local_today,
    parse_time,
    toggle_day,
)

MONDAY = date(2026, 10, 5)
SUNDAY = date(2026, 10, 4)


def test_workdays_mask() -> None:
    assert is_scheduled(WORKDAYS, MONDAY)
    assert not is_scheduled(WORKDAYS, SUNDAY)


def test_toggle_day_flips_bit() -> None:
    assert toggle_day(0, 0) == 1
    assert toggle_day(1, 0) == 0


@pytest.mark.parametrize(
    ("mask", "expected"),
    [
        (0b1111111, "каждый день"),
        (0b0011111, "по будням"),
        (0b1100000, "по выходным"),
        (0b0010101, "Пн, Ср, Пт"),
    ],
)
def test_format_days(mask: int, expected: str) -> None:
    assert format_days(mask) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("21:00", time(21, 0)),
        ("9.30", time(9, 30)),
        ("7 15", time(7, 15)),
        (" 8 ", time(8, 0)),
        ("24:00", None),
        ("12:60", None),
        ("завтра", None),
        ("", None),
    ],
)
def test_parse_time(text: str, expected: time | None) -> None:
    assert parse_time(text) == expected


def test_local_today_crosses_midnight_in_almaty() -> None:
    # 20:30 UTC 4 октября = 01:30 5 октября в Алматы (UTC+5)
    now = datetime(2026, 10, 4, 20, 30, tzinfo=UTC)
    assert local_today("Asia/Almaty", now) == date(2026, 10, 5)
    assert local_today("UTC", now) == date(2026, 10, 4)


def test_can_mark_only_today_and_yesterday() -> None:
    today = date(2026, 10, 4)
    assert can_mark(today, today)
    assert can_mark(date(2026, 10, 3), today)
    assert not can_mark(date(2026, 10, 2), today)
    assert not can_mark(date(2026, 10, 5), today)


def test_format_date() -> None:
    assert format_date(SUNDAY) == "4 октября"
