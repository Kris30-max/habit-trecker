from contextlib import suppress
from datetime import date

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts
from bot.db.models import HabitStatus, User
from bot.db.repositories import habits as habits_repo
from bot.handlers.formatting import day_text
from bot.keyboards.callbacks import HabitAction, HabitCb
from bot.keyboards.habits import day_keyboard
from bot.services.habits import day_items
from bot.services.schedule import can_mark, local_today

router = Router(name="today")

MARK_ACTIONS = {
    HabitAction.DONE: (HabitStatus.DONE, texts.MARKED_DONE),
    HabitAction.SKIP: (HabitStatus.SKIPPED, texts.MARKED_SKIPPED),
    HabitAction.UNDO: (None, texts.MARK_REMOVED),
}


@router.message(Command("today"))
async def cmd_today(message: Message, session: AsyncSession, user: User) -> None:
    today = local_today(user.timezone)
    items = await day_items(session, user.id, today)
    await message.answer(day_text(items, today, today), reply_markup=day_keyboard(items, today))


@router.callback_query(HabitCb.filter(F.action.in_(MARK_ACTIONS)))
async def mark_habit(
    query: CallbackQuery, callback_data: HabitCb, session: AsyncSession, user: User
) -> None:
    day = date.fromisoformat(callback_data.day)
    today = local_today(user.timezone)
    if not can_mark(day, today):
        await query.answer(texts.MARK_TOO_LATE, show_alert=True)
        return

    habit = await habits_repo.get_owned(session, callback_data.habit_id, user.id)
    if habit is None or habit.is_archived:
        await query.answer(texts.HABIT_NOT_FOUND, show_alert=True)
        return

    status, toast = MARK_ACTIONS[callback_data.action]
    await habits_repo.set_status(session, habit.id, day, status)

    items = await day_items(session, user.id, day)
    if isinstance(query.message, Message):
        # Двойное нажатие даёт тот же текст — Telegram отвечает «message is not modified»
        with suppress(TelegramBadRequest):
            await query.message.edit_text(
                day_text(items, day, today), reply_markup=day_keyboard(items, day)
            )
    await query.answer(toast)
