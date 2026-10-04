from collections.abc import AsyncIterator

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.base import Base
from bot.db.session import create_engine, create_session_factory


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_engine("sqlite+aiosqlite://")

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_fk(dbapi_conn, _record):  # type: ignore[no-untyped-def]
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield create_session_factory(engine)
    await engine.dispose()


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
