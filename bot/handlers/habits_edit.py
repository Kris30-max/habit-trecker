from datetime import time
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts
from bot.db.models import Habit, User
from bot.db.repositories import habits as habits_repo
from bot.handlers.formatting import reminder_text
from bot.keyboards.callbacks import DaysAction, DaysCb, EditCb, EditField, NoReminderCb
from bot.keyboards.habits import (
    days_keyboard,
    edit_choice_keyboard,
    edit_field_keyboard,
    no_reminder_keyboard,
)
from bot.services.habits import TITLE_MAX_LEN, clean_title
from bot.services.schedule import format_days, parse_time, toggle_day
from bot.states import EditHabit

router = Router(name="habits_edit")

not_command = F.text & ~F.text.startswith("/")


def _summary(habit: Habit) -> dict[str, str]:
    return {
        "title": escape(habit.title),
        "days": format_days(habit.schedule_days).capitalize(),
        "reminder": reminder_text(habit.remind_time),
    }


@router.message(Command("edit"))
async def cmd_edit(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    await state.clear()
    habits = await habits_repo.list_active(session, user.id)
    if not habits:
        await message.answer(texts.LIST_EMPTY)
        return
    await message.answer(texts.EDIT_ASK_HABIT, reply_markup=edit_choice_keyboard(habits))


@router.callback_query(EditCb.filter())
async def edit_pick(
    query: CallbackQuery,
    callback_data: EditCb,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    habit = await habits_repo.get_owned(session, callback_data.habit_id, user.id)
    if habit is None or habit.is_archived or not isinstance(query.message, Message):
        await query.answer(texts.HABIT_NOT_FOUND, show_alert=True)
        return

    field = callback_data.field
    title = escape(habit.title)
    await state.clear()
    if field is None:
        await query.message.edit_text(
            texts.EDIT_ASK_FIELD.format(**_summary(habit)),
            reply_markup=edit_field_keyboard(habit.id),
        )
    elif field == EditField.TITLE:
        await state.set_state(EditHabit.title)
        await query.message.edit_text(texts.EDIT_ASK_TITLE.format(title=title))
    elif field == EditField.DAYS:
        await state.set_state(EditHabit.days)
        await query.message.edit_text(
            texts.EDIT_ASK_DAYS.format(title=title),
            reply_markup=days_keyboard(habit.schedule_days),
        )
    else:
        await state.set_state(EditHabit.remind_time)
        await query.message.edit_text(
            texts.EDIT_ASK_TIME.format(title=title), reply_markup=no_reminder_keyboard()
        )
    if field is not None:
        await state.update_data(habit_id=habit.id, days=habit.schedule_days)
    await query.answer()


async def _editing(state: FSMContext, session: AsyncSession, user: User) -> Habit | None:
    data = await state.get_data()
    habit = await habits_repo.get_owned(session, data.get("habit_id", 0), user.id)
    if habit is None or habit.is_archived:
        await state.clear()
        return None
    return habit


@router.message(EditHabit.title, not_command)
async def edit_title(
    message: Message, state: FSMContext, session: AsyncSession, user: User
) -> None:
    title = clean_title(message.text)
    if title is None:
        await message.answer(texts.ADD_BAD_TITLE.format(max_len=TITLE_MAX_LEN))
        return
    habit = await _editing(state, session, user)
    if habit is None:
        await message.answer(texts.HABIT_NOT_FOUND)
        return
    habit.title = title
    await state.clear()
    await message.answer(texts.EDIT_SAVED.format(**_summary(habit)))


@router.callback_query(EditHabit.days, DaysCb.filter())
async def edit_days(
    query: CallbackQuery,
    callback_data: DaysCb,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    days: int = (await state.get_data())["days"]
    if callback_data.action != DaysAction.DONE:
        if callback_data.action == DaysAction.TOGGLE:
            days = toggle_day(days, callback_data.value)
        else:
            days = callback_data.value
        await state.update_data(days=days)
        if isinstance(query.message, Message):
            await query.message.edit_reply_markup(reply_markup=days_keyboard(days))
        await query.answer()
        return

    if days == 0:
        await query.answer(texts.ADD_NO_DAYS, show_alert=True)
        return
    habit = await _editing(state, session, user)
    if habit is None or not isinstance(query.message, Message):
        await query.answer(texts.HABIT_NOT_FOUND, show_alert=True)
        return
    habit.schedule_days = days
    await state.clear()
    await query.message.edit_text(texts.EDIT_SAVED.format(**_summary(habit)))
    await query.answer()


async def _save_time(
    state: FSMContext, session: AsyncSession, user: User, remind_time: time | None
) -> str:
    habit = await _editing(state, session, user)
    if habit is None:
        return texts.HABIT_NOT_FOUND
    habit.remind_time = remind_time
    # Новое время должно сработать уже сегодня, даже если по старому сегодня напоминали
    habit.last_reminded_on = None
    await state.clear()
    return texts.EDIT_SAVED.format(**_summary(habit))


@router.message(EditHabit.remind_time, not_command)
async def edit_time(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    remind_time = parse_time(message.text or "")
    if remind_time is None:
        await message.answer(texts.ADD_BAD_TIME)
        return
    await message.answer(await _save_time(state, session, user, remind_time))


@router.callback_query(EditHabit.remind_time, NoReminderCb.filter())
async def edit_no_reminder(
    query: CallbackQuery, state: FSMContext, session: AsyncSession, user: User
) -> None:
    text = await _save_time(state, session, user, None)
    if isinstance(query.message, Message):
        await query.message.edit_text(text)
    await query.answer()
