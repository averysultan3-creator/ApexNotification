from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preland import Preland, PrelandStatus


async def create_preland(
    session: AsyncSession,
    *,
    name: str,
    slug: str,
    url: str | None = None,
    client_id: int | None = None,
    offer_name: str | None = None,
) -> Preland:
    preland = Preland(
        name=name.strip(),
        slug=slug.strip(),
        url=url.strip() if url else None,
        client_id=client_id,
        offer_name=offer_name.strip() if offer_name else None,
        status=PrelandStatus.active.value,
    )
    session.add(preland)
    await session.flush()
    await session.refresh(preland)
    return preland


async def get_preland_by_id(session: AsyncSession, preland_id: int) -> Optional[Preland]:
    return (await session.execute(select(Preland).where(Preland.id == preland_id))).scalar_one_or_none()


async def get_preland_by_slug(session: AsyncSession, slug: str) -> Optional[Preland]:
    return (await session.execute(select(Preland).where(Preland.slug == slug))).scalar_one_or_none()


async def list_prelands(session: AsyncSession, active_only: bool = False) -> list[Preland]:
    stmt = select(Preland).order_by(Preland.created_at.desc())
    if active_only:
        stmt = stmt.where(Preland.status == PrelandStatus.active.value)
    return list((await session.execute(stmt)).scalars().all())


async def toggle_preland_status(session: AsyncSession, preland_id: int) -> Preland | None:
    preland = await get_preland_by_id(session, preland_id)
    if not preland:
        return None
    preland.status = PrelandStatus.inactive.value if preland.status == PrelandStatus.active.value else PrelandStatus.active.value
    await session.flush()
    await session.refresh(preland)
    return preland
