"""Services for BotUser (panel access accounts)."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.bot_user import BotUser


async def get_bot_user(session: AsyncSession, tg_id: int) -> Optional[BotUser]:
    r = await session.execute(
        select(BotUser).where(BotUser.telegram_user_id == tg_id)
    )
    return r.scalar_one_or_none()


async def get_bot_user_by_id(session: AsyncSession, user_id: int) -> Optional[BotUser]:
    return await session.get(BotUser, user_id)


async def create_bot_user(
    session: AsyncSession,
    tg_id: int,
    username: Optional[str],
    role: str,
    client_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> BotUser:
    user = BotUser(
        telegram_user_id=tg_id,
        telegram_username=username,
        role=role,
        client_id=client_id,
        notes=notes,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def update_bot_user(
    session: AsyncSession, user_id: int, **fields
) -> Optional[BotUser]:
    user = await session.get(BotUser, user_id)
    if not user:
        return None
    for k, v in fields.items():
        setattr(user, k, v)
    await session.flush()
    await session.refresh(user)
    return user


async def toggle_bot_user(session: AsyncSession, user_id: int) -> Optional[BotUser]:
    user = await session.get(BotUser, user_id)
    if user:
        user.is_active = not user.is_active
        await session.flush()
    return user


async def delete_bot_user(session: AsyncSession, user_id: int) -> bool:
    user = await session.get(BotUser, user_id)
    if user:
        await session.delete(user)
        await session.flush()
        return True
    return False


async def list_bot_users(
    session: AsyncSession, role: Optional[str] = None
) -> List[BotUser]:
    q = select(BotUser)
    if role:
        q = q.where(BotUser.role == role)
    r = await session.execute(q.order_by(BotUser.created_at.desc()))
    return list(r.scalars().all())
