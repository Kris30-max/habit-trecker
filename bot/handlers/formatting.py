from collections.abc import Sequence
from datetime import date, time, timedelta
from html import escape

from bot import texts
from bot.db.models import HabitStatus
from bot.keyboards.habits import STATUS_ICON
from bot.services.habits import DayItem
from bot.services.schedule import format_date, plural_days
from bot.services.stats import HabitStats
from bot.services.streaks import DayMark

MARK_ICON = {
    DayMark.DONE: "✅",
    DayMark.SKIPPED: "⏭",
    DayMark.MISSED: "❌",
    DayMark.PENDING: "⬜️",
    DayMark.OFF: "▫️",
}
BAR_WIDTH = 10


def progress_bar(percent: int) -> str:
    filled = round(percent * BAR_WIDTH / 100)
    return "▓" * filled + "░" * (BAR_WIDTH - filled)


def stats_text(stats: Sequence[HabitStats]) -> str:
    if not stats:
        return texts.LIST_EMPTY
    blocks = [texts.STATS_HEADER]
    for s in stats:
        lines = [f"<b>{escape(s.habit.title)}</b>"]
        if s.current:
            lines.append(texts.STATS_STREAK.format(current=plural_days(s.current), best=s.best))
        else:
            lines.append(texts.STATS_NO_STREAK.format(best=s.best))
        percent = s.month.percent
        if percent is None:
            lines.append(texts.STATS_NO_DATA)
        else:
            lines.append(
                texts.STATS_MONTH.format(
                    bar=progress_bar(percent),
                    percent=percent,
                    done=s.month.done,
                    planned=s.month.planned,
                )
            )
        lines.append(texts.STATS_WEEK.format(strip="".join(MARK_ICON[m] for m in s.last7)))
        blocks.append("\n".join(lines))
    blocks.append(f"<i>{texts.STATS_LEGEND}</i>")
    return "\n\n".join(blocks)


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
