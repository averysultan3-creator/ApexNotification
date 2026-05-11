from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.preland_link import PrelandLink, PrelandLinkStatus
from app.models.preland_site import PrelandSite


async def create_link(
    session: AsyncSession,
    *,
    site: PrelandSite,
    display_name: str,
    slug: str,
    country: str | None = None,
    placement: str | None = None,
    audience: str | None = None,
    angle: str | None = None,
) -> PrelandLink:
    base = site.base_url.rstrip("/")
    final_url = f"{base}/?pl={slug}"
    link = PrelandLink(
        site_id=site.id,
        display_name=display_name.strip(),
        slug=slug.strip(),
        country=country,
        placement=placement,
        audience=audience,
        angle=angle,
        final_url=final_url,
    )
    session.add(link)
    await session.flush()
    await session.refresh(link)
    return link


async def get_link_by_id(session: AsyncSession, link_id: int) -> PrelandLink | None:
    return (await session.execute(
        select(PrelandLink).where(PrelandLink.id == link_id)
    )).scalar_one_or_none()


async def get_link_by_slug(session: AsyncSession, slug: str) -> PrelandLink | None:
    return (await session.execute(
        select(PrelandLink).where(PrelandLink.slug == slug)
    )).scalar_one_or_none()


async def list_links_for_site(
    session: AsyncSession, site_id: int, active_only: bool = False
) -> list[PrelandLink]:
    stmt = (
        select(PrelandLink)
        .where(PrelandLink.site_id == site_id)
        .order_by(PrelandLink.created_at.desc())
    )
    if active_only:
        stmt = stmt.where(PrelandLink.status == PrelandLinkStatus.active.value)
    else:
        stmt = stmt.where(PrelandLink.status != PrelandLinkStatus.archived.value)
    return list((await session.execute(stmt)).scalars().all())


async def archive_link(session: AsyncSession, link: PrelandLink) -> PrelandLink:
    link.status = PrelandLinkStatus.archived.value
    await session.flush()
    return link


async def generate_unique_slug(session: AsyncSession, slug_base: str) -> str:
    for i in range(1, 999):
        candidate = f"{slug_base}_{i:03d}"
        existing = await get_link_by_slug(session, candidate)
        if not existing:
            return candidate
    import secrets
    return f"{slug_base}_{secrets.token_hex(3)}"
