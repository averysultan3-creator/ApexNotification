from typing import Optional, Tuple, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.offer import Offer, OfferStatus


async def get_offers_paginated(
    session: AsyncSession,
    page: int = 0,
    page_size: int = 10,
    client_id: Optional[int] = None,
    status_filter: Optional[str] = None,
) -> Tuple[List[Offer], int]:
    base_q = select(Offer)
    if client_id:
        base_q = base_q.where(Offer.client_id == client_id)
    if status_filter:
        base_q = base_q.where(Offer.status == status_filter)

    count_result = await session.execute(select(func.count()).select_from(base_q.subquery()))
    total = count_result.scalar_one()

    result = await session.execute(
        base_q.order_by(Offer.name).offset(page * page_size).limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_offers_by_client(session: AsyncSession, client_id: int) -> List[Offer]:
    result = await session.execute(
        select(Offer)
        .where(Offer.client_id == client_id, Offer.status == OfferStatus.active.value)
        .order_by(Offer.name)
    )
    return list(result.scalars().all())


async def get_offer_by_id(session: AsyncSession, offer_id: int) -> Optional[Offer]:
    result = await session.execute(select(Offer).where(Offer.id == offer_id))
    return result.scalar_one_or_none()


async def create_offer(
    session: AsyncSession,
    client_id: int,
    name: str,
    description: Optional[str] = None,
    geo: Optional[str] = None,
    language: Optional[str] = None,
) -> Offer:
    offer = Offer(
        client_id=client_id,
        name=name,
        description=description,
        geo=geo,
        language=language,
        status=OfferStatus.active.value,
    )
    session.add(offer)
    await session.flush()
    await session.refresh(offer)
    return offer


async def update_offer_field(
    session: AsyncSession, offer_id: int, field: str, value: str
) -> Optional[Offer]:
    offer = await get_offer_by_id(session, offer_id)
    if not offer:
        return None
    allowed = {"name", "description", "geo", "language"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' is not editable.")
    setattr(offer, field, value if value else None)
    await session.flush()
    await session.refresh(offer)
    return offer


async def toggle_offer_status(session: AsyncSession, offer_id: int) -> Optional[Offer]:
    offer = await get_offer_by_id(session, offer_id)
    if not offer:
        return None
    offer.status = (
        OfferStatus.inactive.value
        if offer.status == OfferStatus.active.value
        else OfferStatus.active.value
    )
    await session.flush()
    await session.refresh(offer)
    return offer


async def delete_offer(session: AsyncSession, offer_id: int) -> bool:
    offer = await get_offer_by_id(session, offer_id)
    if not offer:
        return False
    await session.delete(offer)
    await session.flush()
    return True
