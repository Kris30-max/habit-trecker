from enum import StrEnum

from aiogram.filters.callback_data import CallbackData


class HabitAction(StrEnum):
    DONE = "done"
    SKIP = "skip"
    UNDO = "undo"
    ARCHIVE = "arch"
    ARCHIVE_YES = "arch_y"
    ARCHIVE_NO = "arch_n"


class HabitCb(CallbackData, prefix="h"):
    action: HabitAction
    habit_id: int
    day: str = ""  # ISO-дата для отметок


class DaysAction(StrEnum):
    TOGGLE = "tg"
    PRESET = "pr"
    DONE = "ok"


class DaysCb(CallbackData, prefix="d"):
    action: DaysAction
    value: int = 0


class NoReminderCb(CallbackData, prefix="nr"):
    pass
