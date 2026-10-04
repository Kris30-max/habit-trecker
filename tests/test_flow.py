"""Сквозные сценарии: апдейты идут через настоящий Dispatcher, Telegram API подменён."""

from datetime import datetime
from itertools import count

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, Update
from aiogram.types import User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.repositories import habits as habits_repo
from bot.db.repositories import users
from bot.dispatcher import build_dispatcher
from bot.keyboards.habits import reminder_keyboard
from bot.services.schedule import local_today
from tests.fakes import FakeSession, make_bot

USER_ID = 100
CHAT = Chat(id=USER_ID, type="private")
TG_USER = TgUser(id=USER_ID, is_bot=False, first_name="Tester")


class Harness:
    def __init__(self, dp: Dispatcher, bot: Bot, session: FakeSession) -> None:
        self.dp, self.bot, self.api = dp, bot, session
        self.ids = count(1)

    async def send(self, text: str, user: TgUser = TG_USER) -> None:
        msg = Message(
            message_id=next(self.ids), date=datetime.now(), chat=CHAT, from_user=user, text=text
        )
        await self.dp.feed_update(self.bot, Update(update_id=next(self.ids), message=msg))

    async def press(self, button_text_prefix: str) -> None:
        data = next(
            d for t, d in self.api.last_markup_buttons() if t.startswith(button_text_prefix)
        )
        await self.press_data(data)

    async def press_data(self, data: str) -> None:
        query = CallbackQuery(
            id=str(next(self.ids)),
            from_user=TG_USER,
            chat_instance="ci",
            data=data,
            message=Message(message_id=1, date=datetime.now(), chat=CHAT, text="..."),
        )
        await self.dp.feed_update(self.bot, Update(update_id=next(self.ids), callback_query=query))


class _FactoryProxy:
    """Роутеры aiogram подключаются один раз, поэтому Dispatcher общий,
    а свежая БД подставляется в него на каждый тест."""

    factory: async_sessionmaker[AsyncSession] | None = None

    def __call__(self) -> AsyncSession:
        assert self.factory is not None
        return self.factory()


_proxy = _FactoryProxy()
_dp = build_dispatcher(_proxy, frozenset({USER_ID}), "Asia/Almaty")  # type: ignore[arg-type]


@pytest.fixture
def harness(session_factory: async_sessionmaker[AsyncSession]) -> Harness:
    _proxy.factory = session_factory
    _dp.fsm.storage = MemoryStorage()
    api = FakeSession()
    return Harness(_dp, make_bot(api), api)


async def test_add_habit_then_mark_done(
    harness: Harness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await harness.send("/add")
    await harness.send("Читать 20 минут")
    await harness.press("Каждый день")
    await harness.press("Готово")
    await harness.send("21:00")
    assert "добавлена" in harness.api.texts()[-1]

    await harness.send("/today")
    assert "⬜️ Читать 20 минут" in harness.api.texts()[-1]

    await harness.press("✅ Читать")
    assert "✅ Читать 20 минут" in harness.api.texts()[-1]
    assert "Всё выполнено" in harness.api.texts()[-1]

    async with session_factory() as s:
        user = await users.get_by_telegram_id(s, USER_ID)
        assert user is not None
        [habit] = await habits_repo.list_active(s, user.id)
        assert habit.remind_time is not None and habit.remind_time.hour == 21


async def test_add_without_reminder_and_cancel(harness: Harness) -> None:
    await harness.send("/add")
    await harness.send("Зарядка")
    await harness.press("Готово")
    await harness.press("🔕")
    assert "без напоминания" in harness.api.texts()[-1]

    await harness.send("/add")
    await harness.send("/cancel")
    assert harness.api.texts()[-1] == "Отменено."


async def test_bad_time_is_rejected(harness: Harness) -> None:
    await harness.send("/add")
    await harness.send("Вода")
    await harness.press("Готово")
    await harness.send("25:99")
    assert "Не понял время" in harness.api.texts()[-1]


async def test_archive_via_delete(harness: Harness) -> None:
    await harness.send("/add")
    await harness.send("Бег")
    await harness.press("Готово")
    await harness.press("🔕")

    await harness.send("/delete")
    await harness.press("🗄 Бег")
    await harness.press("Да, в архив")
    assert "в архиве" in harness.api.texts()[-1]

    await harness.send("/list")
    assert "Пока нет привычек" in harness.api.texts()[-1]


async def test_stats_after_marking(harness: Harness) -> None:
    await harness.send("/add")
    await harness.send("Медитация")
    await harness.press("Готово")
    await harness.press("🔕")
    await harness.send("/today")
    await harness.press("✅ Медитация")

    await harness.send("/stats")
    text = harness.api.texts()[-1]
    assert "<b>Медитация</b>" in text
    assert "Серия: 1 день" in text
    assert "100% (1/1)" in text


async def test_stranger_is_ignored(harness: Harness) -> None:
    stranger = TgUser(id=999, is_bot=False, first_name="X")
    await harness.send("/start", user=stranger)
    assert harness.api.calls == []


async def _habit_id(session_factory: async_sessionmaker[AsyncSession]) -> int:
    async with session_factory() as s:
        user = await users.get_by_telegram_id(s, USER_ID)
        assert user is not None
        [habit] = await habits_repo.list_active(s, user.id)
        return habit.id


def _reminder_button(habit_id: int, prefix: str) -> str:
    markup = reminder_keyboard(habit_id, local_today("Asia/Almaty"))
    return next(
        b.callback_data for row in markup.inline_keyboard for b in row if b.text.startswith(prefix)
    )


async def test_reminder_done_button(
    harness: Harness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await harness.send("/add")
    await harness.send("Витамины")
    await harness.press("Готово")
    await harness.send("10:00")
    habit_id = await _habit_id(session_factory)

    await harness.press_data(_reminder_button(habit_id, "✅"))
    assert harness.api.texts()[-1] == "✅ <b>Витамины</b> — сделано!"

    await harness.send("/today")
    assert "🎉 Всё выполнено!" in harness.api.texts()[-1]


async def test_reminder_snooze_button(
    harness: Harness, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await harness.send("/add")
    await harness.send("Прогулка")
    await harness.press("Готово")
    await harness.send("18:00")
    habit_id = await _habit_id(session_factory)

    await harness.press_data(_reminder_button(habit_id, "⏰"))
    assert "напомню в" in harness.api.texts()[-1]

    async with session_factory() as s:
        habit = await habits_repo.get_owned(s, habit_id, 1)
        assert habit is not None and habit.snoozed_until is not None
