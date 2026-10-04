from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.models import User
from bot.keyboards.callbacks import SettingsAction, SettingsCb

TIMEZONES = (
    ("Asia/Almaty", "Казахстан (UTC+5)"),
    ("Asia/Tashkent", "Узбекистан (UTC+5)"),
    ("Asia/Bishkek", "Кыргызстан (UTC+6)"),
    ("Europe/Moscow", "Москва (UTC+3)"),
)


def settings_keyboard(user: User) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    reminders = "🔔 Напоминания: вкл" if user.reminders_enabled else "🔕 Напоминания: выкл"
    summary = (
        f"🌙 Сводка: {user.summary_time.strftime('%H:%M')}"
        if user.summary_time
        else "🌙 Сводка: выкл"
    )
    kb.button(text=reminders, callback_data=SettingsCb(action=SettingsAction.TOGGLE_REMINDERS))
    kb.button(text=summary, callback_data=SettingsCb(action=SettingsAction.SUMMARY))
    kb.button(text="🌍 Часовой пояс", callback_data=SettingsCb(action=SettingsAction.TIMEZONE))
    kb.adjust(1)
    return kb.as_markup()


def summary_off_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Выключить сводку", callback_data=SettingsCb(action=SettingsAction.SUMMARY_OFF))
    return kb.as_markup()


def timezone_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for tz, label in TIMEZONES:
        kb.button(
            text=label, callback_data=SettingsCb(action=SettingsAction.SET_TIMEZONE, value=tz)
        )
    kb.adjust(1)
    return kb.as_markup()
