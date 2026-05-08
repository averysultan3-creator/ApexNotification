from __future__ import annotations
from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lead import Lead


async def create_lead(
    session: AsyncSession,
    *,
    client_id: int | None = None,
    facebook_form_id: int | None = None,
    fb_lead_id: str | None = None,
    full_name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    raw_data_json: str | None = None,
) -> Lead:
    lead = Lead(
        client_id=client_id,
        facebook_form_id=facebook_form_id,
        fb_lead_id=fb_lead_id,
        full_name=full_name,
        phone=phone,
        email=email,
        raw_data_json=raw_data_json,
    )
    session.add(lead)
    await session.flush()
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
    stmt = (
        select(Lead)
        .where(func.date(Lead.created_at) == today)
        .order_by(Lead.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_leads_last_n(session: AsyncSession, n: int = 20) -> list[Lead]:
    stmt = select(Lead).order_by(Lead.created_at.desc()).limit(n)
    return list((await session.execute(stmt)).scalars().all())


async def list_leads_errors(session: AsyncSession) -> list[Lead]:
    stmt = (
        select(Lead)
        .where(Lead.delivery_error.isnot(None))
        .order_by(Lead.created_at.desc())
        .limit(50)
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_leads_by_form(session: AsyncSession, form_id: int) -> list[Lead]:
    stmt = (
        select(Lead)
        .where(Lead.facebook_form_id == form_id)
        .order_by(Lead.created_at.desc())
        .limit(50)
    )
    return list((await session.execute(stmt)).scalars().all())


async def update_lead_delivery(
    session: AsyncSession,
    lead: Lead,
    *,
    delivered_telegram: bool | None = None,
    delivered_sheet: bool | None = None,
    delivery_error: str | None = None,
) -> Lead:
    if delivered_telegram is not None:
        lead.delivered_telegram = delivered_telegram
    if delivered_sheet is not None:
        lead.delivered_sheet = delivered_sheet
    if delivery_error is not None:
        lead.delivery_error = delivery_error
    await session.flush()
    return lead
