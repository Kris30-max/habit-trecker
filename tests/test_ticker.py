from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.models import ALL_DAYS, Habit, HabitStatus, User
from bot.db.repositories import habits as habits_repo
from bot.db.repositories import users
from bot.scheduler.ticker import tick
from bot.services.schedule import WORKDAYS
from tests.fakes import FakeSession, make_bot

TG_ID = 555
TZ = "Asia/Almaty"  # UTC+5
CREATED = datetime(2026, 10, 1, 0, 0, tzinfo=UTC)
MONDAY = date(2026, 10, 5)


def at(hh: int, mm: int, day: date = MONDAY) -> datetime:
    """Момент по Алматы, переведённый в UTC."""
    return datetime(day.year, day.month, day.day, hh, mm, tzinfo=UTC) - timedelta(hours=5)


async def _setup(
    factory: async_sessionmaker[AsyncSession],
    remind: time | None = time(10, 0),
    schedule_days: int = ALL_DAYS,
    created: datetime = CREATED,
    summary: time | None = None,
) -> int:
    async with factory() as s:
        user = await users.get_or_create(s, TG_ID, "T", TZ)
        user.summary_time = summary
        habit = await habits_repo.create(s, user.id, "Читать", schedule_days, remind)
        habit.created_at = created
        await s.commit()
        return habit.id


async def _run(
    factory: async_sessionmaker[AsyncSession], now: datetime, api: FakeSession
) -> list[str]:
    before = len(api.sent())
    await tick(make_bot(api), factory, now)
    return [m.text for m in api.sent()[before:]]


async def test_reminder_sent_once(session_factory: async_sessionmaker[AsyncSession]) -> None:
    await _setup(session_factory)
    api = FakeSession()

    assert await _run(session_factory, at(9, 59), api) == []
    assert await _run(session_factory, at(10, 0), api) == ["🔔 Пора: <b>Читать</b>"]
    assert await _run(session_factory, at(10, 1), api) == []
    assert [b for b, _ in api.last_markup_buttons()] == [
        "✅ Сделал",
        "⏭ Пропустить",
        "⏰ Через час",
    ]


async def test_reminder_sent_again_next_day(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(session_factory)
    api = FakeSession()
    await _run(session_factory, at(10, 0), api)
    assert len(await _run(session_factory, at(10, 0, MONDAY + timedelta(days=1)), api)) == 1


@pytest.mark.parametrize(("hh", "mm", "sent"), [(11, 59, 1), (12, 0, 0)])
async def test_catch_up_window(
    session_factory: async_sessionmaker[AsyncSession], hh: int, mm: int, sent: int
) -> None:
    await _setup(session_factory)
    assert len(await _run(session_factory, at(hh, mm), FakeSession())) == sent


async def test_no_reminder_when_already_marked(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    habit_id = await _setup(session_factory)
    async with session_factory() as s:
        await habits_repo.set_status(s, habit_id, MONDAY, HabitStatus.DONE)
        await s.commit()
    assert await _run(session_factory, at(10, 0), FakeSession()) == []


async def test_no_reminder_on_unscheduled_day(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(session_factory, schedule_days=WORKDAYS)
    sunday = MONDAY - timedelta(days=1)
    assert await _run(session_factory, at(10, 0, sunday), FakeSession()) == []


async def test_no_reminder_for_habit_created_after_time(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(session_factory, created=at(10, 30))
    assert await _run(session_factory, at(10, 31), FakeSession()) == []


async def test_reminder_shows_streak(session_factory: async_sessionmaker[AsyncSession]) -> None:
    habit_id = await _setup(session_factory)
    async with session_factory() as s:
        for offset in (1, 2, 3):
            await habits_repo.set_status(
                s, habit_id, MONDAY - timedelta(days=offset), HabitStatus.DONE
            )
        await s.commit()
    [text] = await _run(session_factory, at(10, 0), FakeSession())
    assert "Серия: 3 дня 🔥" in text


async def test_snoozed_reminder(session_factory: async_sessionmaker[AsyncSession]) -> None:
    habit_id = await _setup(session_factory, remind=None)
    async with session_factory() as s:
        habit = await s.get(Habit, habit_id)
        assert habit is not None
        habit.snoozed_until = at(11, 0)
        await s.commit()
    api = FakeSession()

    assert await _run(session_factory, at(10, 59), api) == []
    assert await _run(session_factory, at(11, 0), api) == ["🔔 Пора: <b>Читать</b>"]
    assert await _run(session_factory, at(11, 1), api) == []
    async with session_factory() as s:
        habit = await s.get(Habit, habit_id)
        assert habit is not None and habit.snoozed_until is None


async def test_evening_summary_once(session_factory: async_sessionmaker[AsyncSession]) -> None:
    await _setup(session_factory, remind=None, summary=time(21, 0))
    api = FakeSession()

    [text] = await _run(session_factory, at(21, 0), api)
    assert text.startswith("🌙 <b>Итоги дня</b>")
    assert "⬜️ Читать" in text
    assert await _run(session_factory, at(21, 5), api) == []


async def test_blocked_user_gets_reminders_disabled(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(session_factory)
    await _run(session_factory, at(10, 0), FakeSession(blocked_chats=frozenset({TG_ID})))
    async with session_factory() as s:
        user = await users.get_by_telegram_id(s, TG_ID)
        assert isinstance(user, User) and user.reminders_enabled is False
