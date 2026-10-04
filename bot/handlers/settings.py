from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import texts
from bot.db.models import User
from bot.keyboards.callbacks import SettingsAction, SettingsCb
from bot.keyboards.settings import settings_keyboard, summary_off_keyboard, timezone_keyboard
from bot.services.schedule import local_now, parse_time
from bot.states import SettingsForm

router = Router(name="settings")

not_command = F.text & ~F.text.startswith("/")


def settings_text(user: User) -> str:
    return texts.SETTINGS.format(
        tz=user.timezone,
        now=local_now(user.timezone).strftime("%H:%M"),
        reminders=texts.SETTINGS_ON if user.reminders_enabled else texts.SETTINGS_OFF,
        summary=user.summary_time.strftime("%H:%M")
        if user.summary_time
        else texts.SETTINGS_SUMMARY_OFF,
    )


def is_valid_tz(name: str) -> bool:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


async def _show(message: Message, user: User, edit: bool = False) -> None:
    if edit:
        await message.edit_text(settings_text(user), reply_markup=settings_keyboard(user))
    else:
        await message.answer(settings_text(user), reply_markup=settings_keyboard(user))


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext, user: User) -> None:
    await state.clear()
    await _show(message, user)


@router.callback_query(SettingsCb.filter())
async def settings_action(
    query: CallbackQuery, callback_data: SettingsCb, state: FSMContext, user: User
) -> None:
    if not isinstance(query.message, Message):
        await query.answer()
        return
    action = callback_data.action

    if action == SettingsAction.TOGGLE_REMINDERS:
        user.reminders_enabled = not user.reminders_enabled
        await _show(query.message, user, edit=True)
    elif action == SettingsAction.SUMMARY:
        await state.set_state(SettingsForm.summary_time)
        await query.message.edit_text(
            texts.SETTINGS_ASK_SUMMARY, reply_markup=summary_off_keyboard()
        )
    elif action == SettingsAction.SUMMARY_OFF:
        await state.clear()
        user.summary_time = None
        await _show(query.message, user, edit=True)
    elif action == SettingsAction.TIMEZONE:
        await state.set_state(SettingsForm.timezone)
        await query.message.edit_text(texts.SETTINGS_ASK_TZ, reply_markup=timezone_keyboard())
    elif action == SettingsAction.SET_TIMEZONE and is_valid_tz(callback_data.value):
        await state.clear()
        user.timezone = callback_data.value
        await _show(query.message, user, edit=True)
    await query.answer()


@router.message(SettingsForm.summary_time, not_command)
async def got_summary_time(message: Message, state: FSMContext, user: User) -> None:
    summary_time = parse_time(message.text or "")
    if summary_time is None:
        await message.answer(texts.ADD_BAD_TIME)
        return
    user.summary_time = summary_time
    user.last_summary_on = None  # новое время должно сработать уже сегодня
    await state.clear()
    await message.answer(texts.SETTINGS_SAVED)
    await _show(message, user)


@router.message(SettingsForm.timezone, not_command)
async def got_timezone(message: Message, state: FSMContext, user: User) -> None:
    name = (message.text or "").strip()
    if not is_valid_tz(name):
        await message.answer(texts.SETTINGS_BAD_TZ)
        return
    user.timezone = name
    await state.clear()
    await message.answer(texts.SETTINGS_SAVED)
    await _show(message, user)
