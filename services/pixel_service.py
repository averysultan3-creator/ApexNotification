"""Services for Pixel configuration."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.pixel import Pixel, _DEFAULT_EVENTS


async def get_pixels(
    session: AsyncSession,
    scope_type: Optional[str] = None,
    scope_id: Optional[int] = None,
    active_only: bool = False,
) -> List[Pixel]:
    q = select(Pixel)
    if scope_type is not None:
        q = q.where(Pixel.scope_type == scope_type)
    if scope_id is not None:
        q = q.where(Pixel.scope_id == scope_id)
    if active_only:
        q = q.where(Pixel.is_active.is_(True))
    r = await session.execute(q.order_by(Pixel.created_at.desc()))
    return list(r.scalars().all())


async def get_all_pixels(session: AsyncSession) -> List[Pixel]:
    r = await session.execute(select(Pixel).order_by(Pixel.created_at.desc()))
    return list(r.scalars().all())


async def get_pixel_by_id(session: AsyncSession, pixel_id: int) -> Optional[Pixel]:
    return await session.get(Pixel, pixel_id)


async def create_pixel(
    session: AsyncSession,
    name: str,
    pixel_type: str,
    pixel_value: Optional[str] = None,
    scope_type: str = "global",
    scope_id: Optional[int] = None,
    events: Optional[str] = None,
) -> Pixel:
    px = Pixel(
        name=name,
        pixel_type=pixel_type,
        pixel_value=pixel_value,
        scope_type=scope_type,
        scope_id=scope_id,
        events=events or _DEFAULT_EVENTS,
    )
    session.add(px)
    await session.flush()
    await session.refresh(px)
    return px


async def toggle_pixel(session: AsyncSession, pixel_id: int) -> Optional[Pixel]:
    px = await session.get(Pixel, pixel_id)
    if px:
        px.is_active = not px.is_active
        await session.flush()
    return px


async def delete_pixel(session: AsyncSession, pixel_id: int) -> bool:
    px = await session.get(Pixel, pixel_id)
    if px:
        await session.delete(px)
        await session.flush()
        return True
    return False


async def update_pixel_events(
    session: AsyncSession, pixel_id: int, events: List[str]
) -> Optional[Pixel]:
    px = await session.get(Pixel, pixel_id)
    if px:
        px.events = ",".join(events)
        await session.flush()
    return px
