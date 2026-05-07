import json
from typing import Optional, Tuple, List, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.lead import Lead, LeadStatus


async def get_leads_paginated(
    session: AsyncSession,
    page: int = 0,
    page_size: int = 10,
    filters: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Lead], int]:
    base_q = select(Lead)
    if filters:
        if filters.get("client_id"):
            base_q = base_q.where(Lead.client_id == int(filters["client_id"]))
        if filters.get("offer_id"):
            base_q = base_q.where(Lead.offer_id == int(filters["offer_id"]))
        if filters.get("form_id"):
            base_q = base_q.where(Lead.form_id == int(filters["form_id"]))
        if filters.get("ref_id"):
            base_q = base_q.where(Lead.referral_source_id == int(filters["ref_id"]))
        if filters.get("status"):
            base_q = base_q.where(Lead.status == filters["status"])
        if filters.get("date_from"):
            base_q = base_q.where(Lead.created_at >= filters["date_from"])
        if filters.get("date_to"):
            # Include the entire day: "2024-05-07" → "<= 2024-05-07 23:59:59"
            date_to = filters["date_to"]
            if len(date_to) == 10:
                date_to = date_to + " 23:59:59"
            base_q = base_q.where(Lead.created_at <= date_to)

    count_result = await session.execute(select(func.count()).select_from(base_q.subquery()))
    total = count_result.scalar_one()

    result = await session.execute(
        base_q.order_by(Lead.created_at.desc()).offset(page * page_size).limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_lead_by_id(session: AsyncSession, lead_id: int) -> Optional[Lead]:
    result = await session.execute(select(Lead).where(Lead.id == lead_id))
    return result.scalar_one_or_none()


async def check_duplicate_lead(
    session: AsyncSession, form_id: int, telegram_user_id: int
) -> bool:
    """Returns True if lead already exists for this user+form."""
    result = await session.execute(
        select(func.count()).where(
            and_(Lead.form_id == form_id, Lead.telegram_user_id == telegram_user_id)
        )
    )
    return result.scalar_one() > 0


async def create_lead(
    session: AsyncSession,
    form_id: int,
    client_id: int,
    offer_id: int,
    referral_source_id: Optional[int],
    telegram_user_id: int,
    telegram_username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    answers: Dict[str, Any],
) -> Lead:
    lead = Lead(
        form_id=form_id,
        client_id=client_id,
        offer_id=offer_id,
        referral_source_id=referral_source_id,
        telegram_user_id=telegram_user_id,
        telegram_username=telegram_username,
        first_name=first_name,
        last_name=last_name,
        answers_json=json.dumps(answers, ensure_ascii=False),
        status=LeadStatus.new.value,
    )
    session.add(lead)
    await session.flush()
    await session.refresh(lead)
    return lead


async def update_lead_status(
    session: AsyncSession, lead_id: int, status: str
) -> Optional[Lead]:
    lead = await get_lead_by_id(session, lead_id)
    if not lead:
        return None
    if status not in [s.value for s in LeadStatus]:
        raise ValueError(f"Invalid status: {status}")
    lead.status = status
    await session.flush()
    await session.refresh(lead)
    return lead


async def update_lead_notes(
    session: AsyncSession, lead_id: int, notes: str
) -> Optional[Lead]:
    lead = await get_lead_by_id(session, lead_id)
    if not lead:
        return None
    lead.admin_notes = notes
    await session.flush()
    await session.refresh(lead)
    return lead
