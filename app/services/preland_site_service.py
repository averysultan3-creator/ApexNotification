from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.preland_site import PrelandSite, PrelandSiteStatus


async def create_site(session: AsyncSession, *, name: str, base_url: str) -> PrelandSite:
    site = PrelandSite(name=name.strip(), base_url=base_url.strip().rstrip("/"))
    session.add(site)
    await session.flush()
    await session.refresh(site)
    return site


async def get_site_by_id(session: AsyncSession, site_id: int) -> PrelandSite | None:
    return (await session.execute(
        select(PrelandSite).where(PrelandSite.id == site_id)
    )).scalar_one_or_none()


async def list_sites(session: AsyncSession, active_only: bool = False) -> list[PrelandSite]:
    stmt = select(PrelandSite).order_by(PrelandSite.created_at.desc())
    if active_only:
        stmt = stmt.where(PrelandSite.status == PrelandSiteStatus.active.value)
    else:
        stmt = stmt.where(PrelandSite.status != PrelandSiteStatus.archived.value)
    return list((await session.execute(stmt)).scalars().all())


async def list_archived_sites(session: AsyncSession) -> list[PrelandSite]:
    return list((await session.execute(
        select(PrelandSite)
        .where(PrelandSite.status == PrelandSiteStatus.archived.value)
        .order_by(PrelandSite.created_at.desc())
    )).scalars().all())


async def archive_site(session: AsyncSession, site: PrelandSite) -> PrelandSite:
    site.status = PrelandSiteStatus.archived.value
    await session.flush()
    return site


async def restore_site(session: AsyncSession, site: PrelandSite) -> PrelandSite:
    site.status = PrelandSiteStatus.active.value
    await session.flush()
    return site
