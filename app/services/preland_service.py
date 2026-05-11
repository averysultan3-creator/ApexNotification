from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.preland import Preland, PrelandStatus


async def create_preland(
    session: AsyncSession, *, name: str, slug: str, url: str | None = None,
    display_name: str | None = None,
) -> Preland:
    p = Preland(
        name=name.strip(),
        slug=slug.strip(),
        url=url.strip() if url else None,
        display_name=display_name.strip() if display_name else None,
    )
    session.add(p)
    await session.flush()
    await session.refresh(p)
    return p


async def get_preland_by_id(session: AsyncSession, preland_id: int) -> Preland | None:
    return (await session.execute(
        select(Preland).where(Preland.id == preland_id)
    )).scalar_one_or_none()


async def get_preland_by_slug(session: AsyncSession, slug: str) -> Preland | None:
    return (await session.execute(
        select(Preland).where(Preland.slug == slug)
    )).scalar_one_or_none()


async def list_prelands(session: AsyncSession, active_only: bool = False, include_archived: bool = False) -> list[Preland]:
    stmt = select(Preland).order_by(Preland.created_at.desc())
    if active_only:
        stmt = stmt.where(Preland.status == PrelandStatus.active.value)
    elif not include_archived:
        stmt = stmt.where(Preland.status != PrelandStatus.archived.value)
    return list((await session.execute(stmt)).scalars().all())


async def list_archived_prelands(session: AsyncSession) -> list[Preland]:
    return list((await session.execute(
        select(Preland)
        .where(Preland.status == PrelandStatus.archived.value)
        .order_by(Preland.created_at.desc())
    )).scalars().all())


async def archive_preland(session: AsyncSession, preland: Preland) -> Preland:
    preland.status = PrelandStatus.archived.value
    await session.flush()
    return preland


async def restore_preland(session: AsyncSession, preland: Preland) -> Preland:
    preland.status = PrelandStatus.active.value
    await session.flush()
    return preland


async def toggle_preland_status(session: AsyncSession, preland_id: int) -> Preland | None:
    p = await get_preland_by_id(session, preland_id)
    if not p:
        return None
    p.status = (
        PrelandStatus.inactive.value
        if p.status == PrelandStatus.active.value
        else PrelandStatus.active.value
    )
    await session.flush()
    return p
