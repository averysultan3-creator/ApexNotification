from __future__ import annotations
from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lead import Lead


async def create_lead(
    session: AsyncSession,
    *,
    funnel_form_id: int | None = None,
    external_lead_id: str | None = None,
    fb_lead_id: str | None = None,
    fb_form_id: str | None = None,
    fb_page_id: str | None = None,
    form_name: str | None = None,
    full_name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    telegram: str | None = None,
    tag: str | None = None,
    lead_created_time: datetime | None = None,
    raw_data_json: str | None = None,
) -> Lead:
    lead = Lead(
        funnel_form_id=funnel_form_id,
        external_lead_id=external_lead_id,
        fb_lead_id=fb_lead_id,
        fb_form_id=fb_form_id,
        fb_page_id=fb_page_id,
        form_name=form_name,
        full_name=full_name,
        phone=phone,
        email=email,
        telegram=telegram,
        tag=tag,
        lead_created_time=lead_created_time,
        raw_data_json=raw_data_json,
    )
    session.add(lead)
    try:
        await session.flush()
    except IntegrityError:
        # Duplicate (funnel_form_id, external_lead_id) or fb_lead_id — return existing
        await session.rollback()
        if fb_lead_id:
            existing = await get_lead_by_fb_lead_id(session, fb_lead_id)
            if existing:
                return existing
        if funnel_form_id and external_lead_id:
            existing = (await session.execute(
                select(Lead).where(
                    Lead.funnel_form_id == funnel_form_id,
                    Lead.external_lead_id == external_lead_id,
                )
            )).scalar_one_or_none()
            if existing:
                return existing
        raise
    await session.refresh(lead)
    return lead


async def get_lead_by_id(session: AsyncSession, lead_id: int) -> Lead | None:
    return (await session.execute(
        select(Lead).where(Lead.id == lead_id)
    )).scalar_one_or_none()


async def get_lead_by_fb_lead_id(session: AsyncSession, fb_lead_id: str) -> Lead | None:
    return (await session.execute(
        select(Lead).where(Lead.fb_lead_id == fb_lead_id)
    )).scalar_one_or_none()


async def list_leads_today(session: AsyncSession) -> list[Lead]:
    today = datetime.now().date().isoformat()
    result = await session.execute(
        select(Lead)
        .where(func.date(Lead.created_at) == today)
        .order_by(Lead.created_at.desc())
    )
    return list(result.scalars().all())


async def list_leads_by_funnel(
    session: AsyncSession, funnel_form_id: int, limit: int | None = None
) -> list[Lead]:
    q = (
        select(Lead)
        .where(Lead.funnel_form_id == funnel_form_id)
        .order_by(Lead.created_at.desc())
    )
    if limit:
        q = q.limit(limit)
    return list((await session.execute(q)).scalars().all())


async def list_leads_last_n(session: AsyncSession, n: int = 20) -> list[Lead]:
    result = await session.execute(
        select(Lead).order_by(Lead.created_at.desc()).limit(n)
    )
    return list(result.scalars().all())


async def list_leads_errors(session: AsyncSession) -> list[Lead]:
    result = await session.execute(
        select(Lead)
        .where(Lead.delivery_error.isnot(None))
        .order_by(Lead.created_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())
