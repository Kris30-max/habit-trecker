from collections.abc import Sequence
from datetime import date

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.db.models import ALL_DAYS, Habit, HabitStatus
from bot.keyboards.callbacks import (
    DaysAction,
    DaysCb,
    HabitAction,
    HabitCb,
    NoReminderCb,
)
from bot.services.habits import DayItem
from bot.services.schedule import WEEKDAYS, WEEKEND, WORKDAYS

STATUS_ICON = {HabitStatus.DONE: "✅", HabitStatus.SKIPPED: "⏭"}


def days_keyboard(schedule_days: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, name in enumerate(WEEKDAYS):
        mark = "✅" if schedule_days & (1 << i) else "▫️"
        kb.button(text=f"{mark}{name}", callback_data=DaysCb(action=DaysAction.TOGGLE, value=i))
    for text, mask in (("Каждый день", ALL_DAYS), ("Будни", WORKDAYS), ("Выходные", WEEKEND)):
        kb.button(text=text, callback_data=DaysCb(action=DaysAction.PRESET, value=mask))
    kb.button(text="Готово ➡️", callback_data=DaysCb(action=DaysAction.DONE))
    kb.adjust(7, 3, 1)
    return kb.as_markup()


def no_reminder_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔕 Без напоминания", callback_data=NoReminderCb())
    return kb.as_markup()


def day_keyboard(items: Sequence[DayItem], day: date) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    iso = day.isoformat()
    sizes = []
    for item in items:
        habit_id = item.habit.id
        if item.status is None:
            kb.button(
                text=f"✅ {item.habit.title}",
                callback_data=HabitCb(action=HabitAction.DONE, habit_id=habit_id, day=iso),
            )
            kb.button(
                text="⏭",
                callback_data=HabitCb(action=HabitAction.SKIP, habit_id=habit_id, day=iso),
            )
            sizes.append(2)
        else:
            kb.button(
                text=f"↩️ {STATUS_ICON[item.status]} {item.habit.title}",
                callback_data=HabitCb(action=HabitAction.UNDO, habit_id=habit_id, day=iso),
            )
            sizes.append(1)
    kb.adjust(*sizes)
    return kb.as_markup()


def reminder_keyboard(habit_id: int, day: date) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    iso = day.isoformat()
    for text, action in (
        ("✅ Сделал", HabitAction.DONE),
        ("⏭ Пропустить", HabitAction.SKIP),
        ("⏰ Через час", HabitAction.SNOOZE),
    ):
        kb.button(
            text=text,
            callback_data=HabitCb(action=action, habit_id=habit_id, day=iso, reminder=True),
        )
    kb.adjust(2, 1)
    return kb.as_markup()


def archive_choice_keyboard(habits: Sequence[Habit]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for habit in habits:
        kb.button(
            text=f"🗄 {habit.title}",
            callback_data=HabitCb(action=HabitAction.ARCHIVE, habit_id=habit.id),
        )
    kb.adjust(1)
    return kb.as_markup()


def archive_confirm_keyboard(habit_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text="Да, в архив",
        callback_data=HabitCb(action=HabitAction.ARCHIVE_YES, habit_id=habit_id),
    )
    kb.button(
        text="Отмена",
        callback_data=HabitCb(action=HabitAction.ARCHIVE_NO, habit_id=habit_id),
    )
    return kb.as_markup()
