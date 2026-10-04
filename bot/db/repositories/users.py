from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User


async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def get_or_create(
    session: AsyncSession, telegram_id: int, first_name: str | None, timezone: str
) -> User:
    user = await get_by_telegram_id(session, telegram_id)
    if user is None:
        user = User(telegram_id=telegram_id, first_name=first_name, timezone=timezone)
        session.add(user)
        await session.flush()
    elif user.first_name != first_name:
        user.first_name = first_name
    return user
