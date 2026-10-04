from datetime import datetime
from typing import Any

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import EditMessageText, SendMessage, TelegramMethod
from aiogram.types import Chat, Message


class FakeSession(BaseSession):
    """Запоминает вызовы Bot API вместо отправки в Telegram."""

    def __init__(self, blocked_chats: frozenset[int] = frozenset()) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []
        self.blocked_chats = blocked_chats

    async def make_request(self, bot: Bot, method: TelegramMethod[Any], timeout: int | None = None):  # type: ignore[no-untyped-def]
        if isinstance(method, SendMessage) and method.chat_id in self.blocked_chats:
            raise TelegramForbiddenError(method=method, message="bot was blocked by the user")
        self.calls.append(method)
        if isinstance(method, SendMessage | EditMessageText):
            chat_id = getattr(method, "chat_id", None) or 1
            chat = Chat(id=int(chat_id), type="private")
            return Message(message_id=1, date=datetime.now(), chat=chat, text=method.text)
        return True

    async def stream_content(self, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    async def close(self) -> None:
        pass

    def texts(self) -> list[str]:
        return [c.text for c in self.calls if isinstance(c, SendMessage | EditMessageText)]

    def sent(self) -> list[SendMessage]:
        return [c for c in self.calls if isinstance(c, SendMessage)]

    def last_markup_buttons(self) -> list[tuple[str, str]]:
        for call in reversed(self.calls):
            markup = getattr(call, "reply_markup", None)
            if markup is not None:
                return [(b.text, b.callback_data) for row in markup.inline_keyboard for b in row]
        return []


def make_bot(session: FakeSession) -> Bot:
    return Bot("42:TEST", session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
