from __future__ import annotations

from datetime import datetime, time
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead, LeadStatus, SourceType
from app.utils.formatters import dump_json


async def create_lead(
    session: AsyncSession,
    *,
    source_type: str = SourceType.facebook_lead_form.value,
    fb_lead_id: str | None = None,
    fb_page_id: str | None = None,
    fb_form_id: str | None = None,
    client_id: int | None = None,
    form_id: int | None = None,
    raw_data: dict[str, Any] | None = None,
    normalized_data: dict[str, Any] | None = None,
    full_name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    telegram: str | None = None,
) -> Lead:
    lead = Lead(
        source_type=source_type,
        fb_lead_id=fb_lead_id,
        fb_page_id=fb_page_id,
        fb_form_id=fb_form_id,
        client_id=client_id,
        form_id=form_id,
        raw_data_json=dump_json(raw_data or {}),
        normalized_data_json=dump_json(normalized_data or {}),
        full_name=full_name,
        phone=phone,
        email=email,
        telegram=telegram,
        status=LeadStatus.new.value,
    )
    session.add(lead)
    await session.flush()
    await session.refresh(lead)
    return lead


async def get_lead_by_id(session: AsyncSession, lead_id: int) -> Optional[Lead]:
    return (await session.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()


async def get_lead_by_fb_lead_id(session: AsyncSession, fb_lead_id: str) -> Optional[Lead]:
    return (await session.execute(select(Lead).where(Lead.fb_lead_id == str(fb_lead_id)))).scalar_one_or_none()


async def list_leads_today(session: AsyncSession, limit: int = 20) -> list[Lead]:
    today = datetime.combine(datetime.utcnow().date(), time.min)
    stmt = select(Lead).where(Lead.created_at >= today).order_by(Lead.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def list_leads(session: AsyncSession, limit: int = 50) -> list[Lead]:
    stmt = select(Lead).order_by(Lead.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def list_delivery_error_leads(session: AsyncSession, limit: int = 50) -> list[Lead]:
    stmt = select(Lead).where(Lead.status == LeadStatus.delivery_error.value).order_by(Lead.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def count_leads_today(session: AsyncSession) -> int:
    today = datetime.combine(datetime.utcnow().date(), time.min)
    return int((await session.execute(select(func.count()).select_from(Lead).where(Lead.created_at >= today))).scalar_one())


async def mark_lead_delivery_state(
    session: AsyncSession,
    lead: Lead,
    *,
    delivered_telegram: bool | None = None,
    delivered_email: bool | None = None,
    delivered_sheet: bool | None = None,
    has_errors: bool = False,
) -> Lead:
    if delivered_telegram is not None:
        lead.delivered_telegram = delivered_telegram
    if delivered_email is not None:
        lead.delivered_email = delivered_email
    if delivered_sheet is not None:
        lead.delivered_sheet = delivered_sheet
    lead.status = LeadStatus.delivery_error.value if has_errors else LeadStatus.delivered.value
    await session.flush()
    await session.refresh(lead)
    return lead
