from html import escape

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot import texts

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    name = message.from_user.first_name if message.from_user else "друг"
    await message.answer(texts.START.format(name=escape(name)))


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP)
