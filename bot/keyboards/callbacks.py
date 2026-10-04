from enum import StrEnum

from aiogram.filters.callback_data import CallbackData


class HabitAction(StrEnum):
    DONE = "done"
    SKIP = "skip"
    UNDO = "undo"
    SNOOZE = "snz"
    ARCHIVE = "arch"
    ARCHIVE_YES = "arch_y"
    ARCHIVE_NO = "arch_n"


class HabitCb(CallbackData, prefix="h"):
    action: HabitAction
    habit_id: int
    day: str = ""  # ISO-дата для отметок
    reminder: bool = False  # кнопка из сообщения-напоминания


class DaysAction(StrEnum):
    TOGGLE = "tg"
    PRESET = "pr"
    DONE = "ok"


class DaysCb(CallbackData, prefix="d"):
    action: DaysAction
    value: int = 0


class NoReminderCb(CallbackData, prefix="nr"):
    pass


class EditField(StrEnum):
    TITLE = "title"
    DAYS = "days"
    TIME = "time"


class EditCb(CallbackData, prefix="e"):
    habit_id: int
    field: EditField | None = None


class SettingsAction(StrEnum):
    TOGGLE_REMINDERS = "rem"
    SUMMARY = "sum"
    SUMMARY_OFF = "sum_off"
    TIMEZONE = "tz"
    SET_TIMEZONE = "tz_set"


class SettingsCb(CallbackData, prefix="s"):
    action: SettingsAction
    value: str = ""
