from collections.abc import Sequence
from datetime import date, time, timedelta
from html import escape

from bot import texts
from bot.db.models import HabitStatus
from bot.keyboards.habits import STATUS_ICON
from bot.services.habits import DayItem
from bot.services.schedule import format_date


def reminder_text(remind_time: time | None) -> str:
    if remind_time is None:
        return texts.REMINDER_OFF
    return texts.REMINDER_AT.format(time=remind_time.strftime("%H:%M"))


def day_text(items: Sequence[DayItem], day: date, today: date) -> str:
    header = (
        texts.DAY_HEADER_YESTERDAY if day == today - timedelta(days=1) else texts.DAY_HEADER_TODAY
    )
    lines = [header.format(date=format_date(day)), ""]
    if not items:
        lines.append(texts.DAY_EMPTY)
        return "\n".join(lines)

    for item in items:
        icon = STATUS_ICON[item.status] if item.status else "⬜️"
        lines.append(f"{icon} {escape(item.habit.title)}")

    done = sum(item.status == HabitStatus.DONE for item in items)
    lines.append("")
    if done == len(items):
        lines.append(texts.DAY_ALL_DONE)
    else:
        lines.append(texts.DAY_PROGRESS.format(done=done, total=len(items)))
    return "\n".join(lines)
