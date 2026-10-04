from datetime import date, datetime, time
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    false,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base

# В SQLite автоинкремент работает только у INTEGER PRIMARY KEY
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")

ALL_DAYS = 0b1111111  # бит 0 = понедельник … бит 6 = воскресенье


class HabitStatus(StrEnum):
    DONE = "done"
    SKIPPED = "skipped"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    first_name: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(Text)
    summary_time: Mapped[time | None] = mapped_column(Time)
    reminders_enabled: Mapped[bool] = mapped_column(default=True, server_default=true())
    last_summary_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Habit(Base):
    __tablename__ = "habits"
    __table_args__ = (
        CheckConstraint(f"schedule_days BETWEEN 1 AND {ALL_DAYS}", name="schedule_days_range"),
        Index("ix_habits_user_id_is_archived", "user_id", "is_archived"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(64))
    emoji: Mapped[str | None] = mapped_column(String(8))
    schedule_days: Mapped[int] = mapped_column(
        SmallInteger, default=ALL_DAYS, server_default=str(ALL_DAYS)
    )
    remind_time: Mapped[time | None] = mapped_column(Time)
    last_reminded_on: Mapped[date | None] = mapped_column(Date)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_archived: Mapped[bool] = mapped_column(default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HabitLog(Base):
    __tablename__ = "habit_logs"
    __table_args__ = (
        UniqueConstraint("habit_id", "date", name="uq_habit_logs_habit_id_date"),
        CheckConstraint("status IN ('done', 'skipped')", name="status_valid"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    habit_id: Mapped[int] = mapped_column(ForeignKey("habits.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
