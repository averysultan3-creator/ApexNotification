import os

os.environ.setdefault("BOT_TOKEN", "0:test")
os.environ.setdefault("ADMIN_IDS", "12345")
os.environ.setdefault("FACEBOOK_VERIFY_TOKEN", "test_verify")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from database import Base


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionFactory() as sess:
        yield sess
        await sess.rollback()

    await engine.dispose()
