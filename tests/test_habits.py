from datetime import date, time

from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import HabitStatus, User
from bot.db.repositories import habits as habits_repo
from bot.db.repositories import users
from bot.handlers.formatting import day_text
from bot.services.habits import clean_title, day_items
from bot.services.schedule import WEEKEND, WORKDAYS

MONDAY = date(2026, 10, 5)


async def _user(session: AsyncSession, telegram_id: int = 1) -> User:
    return await users.get_or_create(session, telegram_id, None, "Asia/Almaty")


def test_clean_title() -> None:
    assert clean_title("  Читать   20 минут ") == "Читать 20 минут"
    assert clean_title("   ") is None
    assert clean_title("x" * 65) is None


async def test_list_active_skips_archived(session: AsyncSession) -> None:
    user = await _user(session)
    kept = await habits_repo.create(session, user.id, "Читать", WORKDAYS, time(21))
    archived = await habits_repo.create(session, user.id, "Бег", WORKDAYS, None)
    archived.is_archived = True

    assert [h.id for h in await habits_repo.list_active(session, user.id)] == [kept.id]


async def test_get_owned_rejects_foreign_habit(session: AsyncSession) -> None:
    owner = await _user(session, 1)
    stranger = await _user(session, 2)
    habit = await habits_repo.create(session, owner.id, "Читать", WORKDAYS, None)

    assert await habits_repo.get_owned(session, habit.id, owner.id) is habit
    assert await habits_repo.get_owned(session, habit.id, stranger.id) is None


async def test_set_status_updates_and_removes(session: AsyncSession) -> None:
    user = await _user(session)
    habit = await habits_repo.create(session, user.id, "Читать", WORKDAYS, None)

    await habits_repo.set_status(session, habit.id, MONDAY, HabitStatus.SKIPPED)
    await habits_repo.set_status(session, habit.id, MONDAY, HabitStatus.DONE)
    assert await habits_repo.statuses_for_day(session, [habit.id], MONDAY) == {
        habit.id: HabitStatus.DONE
    }

    await habits_repo.set_status(session, habit.id, MONDAY, None)
    assert await habits_repo.statuses_for_day(session, [habit.id], MONDAY) == {}


async def test_day_items_only_scheduled(session: AsyncSession) -> None:
    user = await _user(session)
    weekday = await habits_repo.create(session, user.id, "Работа", WORKDAYS, None)
    await habits_repo.create(session, user.id, "Отдых", WEEKEND, None)
    await habits_repo.set_status(session, weekday.id, MONDAY, HabitStatus.DONE)

    items = await day_items(session, user.id, MONDAY)

    assert [(i.habit.title, i.status) for i in items] == [("Работа", HabitStatus.DONE)]


async def test_day_text_escapes_and_counts(session: AsyncSession) -> None:
    user = await _user(session)
    a = await habits_repo.create(session, user.id, "<b>Вода</b>", WORKDAYS, None)
    await habits_repo.create(session, user.id, "Чтение", WORKDAYS, None)
    await habits_repo.set_status(session, a.id, MONDAY, HabitStatus.DONE)

    text = day_text(await day_items(session, user.id, MONDAY), MONDAY, MONDAY)

    assert "Сегодня, 5 октября" in text
    assert "✅ &lt;b&gt;Вода&lt;/b&gt;" in text
    assert "⬜️ Чтение" in text
    assert "Выполнено 1 из 2" in text
