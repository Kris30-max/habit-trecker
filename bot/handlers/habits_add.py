from datetime import time
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts
from bot.db.models import ALL_DAYS, User
from bot.db.repositories import habits as habits_repo
from bot.handlers.formatting import reminder_text
from bot.keyboards.callbacks import DaysAction, DaysCb, NoReminderCb
from bot.keyboards.habits import days_keyboard, no_reminder_keyboard
from bot.services.habits import TITLE_MAX_LEN, clean_title
from bot.services.schedule import format_days, parse_time, toggle_day
from bot.states import AddHabit

router = Router(name="habits_add")

not_command = F.text & ~F.text.startswith("/")


@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddHabit.title)
    await message.answer(texts.ADD_ASK_TITLE)


@router.message(AddHabit.title, not_command)
async def got_title(message: Message, state: FSMContext) -> None:
    title = clean_title(message.text)
    if title is None:
        await message.answer(texts.ADD_BAD_TITLE.format(max_len=TITLE_MAX_LEN))
        return
    await state.update_data(title=title, days=ALL_DAYS)
    await state.set_state(AddHabit.days)
    await message.answer(
        texts.ADD_ASK_DAYS.format(title=escape(title)), reply_markup=days_keyboard(ALL_DAYS)
    )


@router.callback_query(AddHabit.days, DaysCb.filter())
async def got_days(query: CallbackQuery, callback_data: DaysCb, state: FSMContext) -> None:
    data = await state.get_data()
    days: int = data["days"]

    if callback_data.action == DaysAction.DONE:
        if days == 0:
            await query.answer(texts.ADD_NO_DAYS, show_alert=True)
            return
        await state.set_state(AddHabit.remind_time)
        if isinstance(query.message, Message):
            await query.message.edit_text(
                texts.ADD_DAYS_CHOSEN.format(title=escape(data["title"]), days=format_days(days))
            )
            await query.message.answer(texts.ADD_ASK_TIME, reply_markup=no_reminder_keyboard())
        await query.answer()
        return

    if callback_data.action == DaysAction.TOGGLE:
        days = toggle_day(days, callback_data.value)
    else:
        days = callback_data.value
    await state.update_data(days=days)
    if isinstance(query.message, Message):
        await query.message.edit_reply_markup(reply_markup=days_keyboard(days))
    await query.answer()


@router.message(AddHabit.remind_time, not_command)
async def got_time(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    remind_time = parse_time(message.text or "")
    if remind_time is None:
        await message.answer(texts.ADD_BAD_TIME)
        return
    await message.answer(await _finish(state, session, user, remind_time))


@router.callback_query(AddHabit.remind_time, NoReminderCb.filter())
async def got_no_reminder(
    query: CallbackQuery, state: FSMContext, session: AsyncSession, user: User
) -> None:
    text = await _finish(state, session, user, None)
    if isinstance(query.message, Message):
        await query.message.edit_text(text)
    await query.answer()


async def _finish(
    state: FSMContext, session: AsyncSession, user: User, remind_time: time | None
) -> str:
    data = await state.get_data()
    habit = await habits_repo.create(session, user.id, data["title"], data["days"], remind_time)
    await state.clear()
    return texts.ADD_DONE.format(
        title=escape(habit.title),
        days=format_days(habit.schedule_days).capitalize(),
        reminder=reminder_text(habit.remind_time),
    )
