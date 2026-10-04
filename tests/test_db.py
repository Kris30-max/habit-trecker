from datetime import date
from typing import Any

import pytest
from aiogram.types import User as TgUser
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.models import Habit, HabitLog, HabitStatus, User
from bot.db.repositories import users
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.user import UserMiddleware


async def test_get_or_create_registers_user_once(session: AsyncSession) -> None:
    first = await users.get_or_create(session, 42, "Ann", "Europe/Moscow")
    second = await users.get_or_create(session, 42, "Anna", "Europe/Moscow")

    assert first.id == second.id
    assert second.first_name == "Anna"
    assert await session.scalar(select(func.count()).select_from(User)) == 1


async def test_habit_defaults(session: AsyncSession) -> None:
    user = await users.get_or_create(session, 1, None, "Europe/Moscow")
    habit = Habit(user_id=user.id, title="Читать")
    session.add(habit)
    await session.flush()

    assert habit.schedule_days == 0b1111111
    assert habit.is_archived is False


async def test_one_log_per_habit_per_day(session: AsyncSession) -> None:
    user = await users.get_or_create(session, 1, None, "Europe/Moscow")
    habit = Habit(user_id=user.id, title="Зарядка")
    session.add(habit)
    await session.flush()

    day = date(2026, 10, 4)
    session.add(HabitLog(habit_id=habit.id, date=day, status=HabitStatus.DONE))
    await session.flush()
    session.add(HabitLog(habit_id=habit.id, date=day, status=HabitStatus.SKIPPED))
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_middlewares_commit_registered_user(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    tg_user = TgUser(id=7, is_bot=False, first_name="Test")

    async def handler(event: Any, data: dict[str, Any]) -> int:
        return data["user"].telegram_id

    async def with_user(event: Any, data: dict[str, Any]) -> int:
        return await UserMiddleware("Europe/Moscow")(handler, event, data)

    result = await DbSessionMiddleware(session_factory)(
        with_user, object(), {"event_from_user": tg_user}
    )

    assert result == 7
    async with session_factory() as fresh:
        assert await users.get_by_telegram_id(fresh, 7) is not None


async def test_middleware_rolls_back_on_error(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async def failing(event: Any, data: dict[str, Any]) -> None:
        await users.get_or_create(data["session"], 8, None, "Europe/Moscow")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await DbSessionMiddleware(session_factory)(failing, object(), {})

    async with session_factory() as fresh:
        assert await users.get_by_telegram_id(fresh, 8) is None
