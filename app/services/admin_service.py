from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.admin import Admin
from config import ADMIN_IDS


async def is_admin_in_db(session: AsyncSession, telegram_user_id: int) -> bool:
    row = await session.execute(
        select(Admin.id).where(Admin.telegram_user_id == telegram_user_id)
    )
    return row.scalar_one_or_none() is not None


async def is_admin(session: AsyncSession, telegram_user_id: int) -> bool:
    """Check ADMIN_IDS fallback OR admins table."""
    if telegram_user_id in ADMIN_IDS:
        return True
    return await is_admin_in_db(session, telegram_user_id)


async def get_admin(session: AsyncSession, telegram_user_id: int) -> Admin | None:
    row = await session.execute(
        select(Admin).where(Admin.telegram_user_id == telegram_user_id)
    )
    return row.scalar_one_or_none()


async def add_admin(
    session: AsyncSession,
    telegram_user_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> tuple[Admin, bool]:
    """
    Add user as admin. Returns (admin, is_new).
    If already exists — returns existing record, is_new=False.
    """
    existing = await get_admin(session, telegram_user_id)
    if existing:
        return existing, False

    admin = Admin(
        telegram_user_id=telegram_user_id,
        username=username,
        first_name=first_name,
        added_by_command=True,
    )
    session.add(admin)
    await session.flush()
    return admin, True
