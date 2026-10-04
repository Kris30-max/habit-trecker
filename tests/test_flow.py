"""Сквозные сценарии: апдейты идут через настоящий Dispatcher, Telegram API подменён."""

from datetime import datetime
from itertools import count
from typing import Any

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import EditMessageText, SendMessage, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Message, Update
from aiogram.types import User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.repositories import habits as habits_repo
from bot.db.repositories import users
from bot.dispatcher import build_dispatcher

USER_ID = 100
CHAT = Chat(id=USER_ID, type="private")
TG_USER = TgUser(id=USER_ID, is_bot=False, first_name="Tester")


class FakeSession(BaseSession):
    """Запоминает вызовы Bot API вместо отправки в Telegram."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []

    async def make_request(self, bot: Bot, method: TelegramMethod[Any], timeout: int | None = None):  # type: ignore[no-untyped-def]
        self.calls.append(method)
        if isinstance(method, SendMessage | EditMessageText):
            return Message(message_id=1, date=datetime.now(), chat=CHAT, text=method.text)
        return True

    async def stream_content(self, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    async def close(self) -> None:
        pass

    def texts(self) -> list[str]:
        return [c.text for c in self.calls if isinstance(c, SendMessage | EditMessageText)]

    def last_markup_buttons(self) -> list[tuple[str, str]]:
        for call in reversed(self.calls):
            markup = getattr(call, "reply_markup", None)
            if markup is not None:
                return [(b.text, b.callback_data) for row in markup.inline_keyboard for b in row]
        return []


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
    bot = Bot("42:TEST", session=api, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    return Harness(_dp, bot, api)


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


async def test_stranger_is_ignored(harness: Harness) -> None:
    stranger = TgUser(id=999, is_bot=False, first_name="X")
    await harness.send("/start", user=stranger)
    assert harness.api.calls == []
