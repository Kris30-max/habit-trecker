from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts
from bot.db.models import User
from bot.db.repositories import habits as habits_repo
from bot.handlers.formatting import reminder_text
from bot.keyboards.callbacks import HabitAction, HabitCb
from bot.keyboards.habits import archive_choice_keyboard, archive_confirm_keyboard
from bot.services.schedule import format_days

router = Router(name="habits_list")


@router.message(Command("list"))
async def cmd_list(message: Message, session: AsyncSession, user: User) -> None:
    habits = await habits_repo.list_active(session, user.id)
    if not habits:
        await message.answer(texts.LIST_EMPTY)
        return
    lines = [texts.LIST_HEADER, ""]
    for n, habit in enumerate(habits, start=1):
        lines.append(
            texts.LIST_ITEM.format(
                n=n,
                title=escape(habit.title),
                days=format_days(habit.schedule_days),
                reminder=reminder_text(habit.remind_time),
            )
        )
    await message.answer("\n".join(lines))


@router.message(Command("delete"))
async def cmd_delete(message: Message, session: AsyncSession, user: User) -> None:
    habits = await habits_repo.list_active(session, user.id)
    if not habits:
        await message.answer(texts.LIST_EMPTY)
        return
    await message.answer(texts.DELETE_ASK, reply_markup=archive_choice_keyboard(habits))


@router.callback_query(
    HabitCb.filter(
        F.action.in_({HabitAction.ARCHIVE, HabitAction.ARCHIVE_YES, HabitAction.ARCHIVE_NO})
    )
)
async def archive_flow(
    query: CallbackQuery, callback_data: HabitCb, session: AsyncSession, user: User
) -> None:
    habit = await habits_repo.get_owned(session, callback_data.habit_id, user.id)
    if habit is None or habit.is_archived or not isinstance(query.message, Message):
        await query.answer(texts.HABIT_NOT_FOUND, show_alert=True)
        return

    title = escape(habit.title)
    if callback_data.action == HabitAction.ARCHIVE:
        await query.message.edit_text(
            texts.DELETE_CONFIRM.format(title=title),
            reply_markup=archive_confirm_keyboard(habit.id),
        )
    elif callback_data.action == HabitAction.ARCHIVE_YES:
        habit.is_archived = True
        await query.message.edit_text(texts.DELETE_DONE.format(title=title))
    else:
        await query.message.edit_text(texts.CANCELLED)
    await query.answer()
