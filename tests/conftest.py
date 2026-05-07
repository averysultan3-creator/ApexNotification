import os
os.environ.setdefault("BOT_TOKEN", "0:test")
os.environ.setdefault("ADMIN_IDS", "12345")

import pytest
import pytest_asyncio
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database import Base


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    import models  # noqa: F401
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionFactory() as sess:
        yield sess
        await sess.rollback()
