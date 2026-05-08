from __future__ import annotations

from datetime import datetime, time
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.facebook_lead_form import FacebookLeadForm, FacebookLeadFormStatus
from app.models.lead import Lead, LeadStatus


async def create_facebook_form(
    session: AsyncSession,
    *,
    name: str,
    fb_page_id: str,
    fb_form_id: str,
    client_id: int,
    offer_name: str | None = None,
) -> FacebookLeadForm:
    form = FacebookLeadForm(
        name=name.strip(),
        fb_page_id=fb_page_id.strip(),
        fb_form_id=fb_form_id.strip(),
        client_id=client_id,
        offer_name=offer_name.strip() if offer_name else None,
        status=FacebookLeadFormStatus.active.value,
    )
    session.add(form)
    await session.flush()
    await session.refresh(form)
    return form


async def get_facebook_form_by_id(session: AsyncSession, form_id: int) -> Optional[FacebookLeadForm]:
    return (await session.execute(select(FacebookLeadForm).where(FacebookLeadForm.id == form_id))).scalar_one_or_none()


async def get_facebook_form_by_fb_form_id(session: AsyncSession, fb_form_id: str) -> Optional[FacebookLeadForm]:
    stmt = select(FacebookLeadForm).where(FacebookLeadForm.fb_form_id == str(fb_form_id))
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_facebook_forms(session: AsyncSession, active_only: bool = False) -> list[FacebookLeadForm]:
    stmt = select(FacebookLeadForm).order_by(FacebookLeadForm.created_at.desc())
    if active_only:
        stmt = stmt.where(FacebookLeadForm.status == FacebookLeadFormStatus.active.value)
    return list((await session.execute(stmt)).scalars().all())


async def toggle_facebook_form_status(session: AsyncSession, form_id: int) -> FacebookLeadForm | None:
    form = await get_facebook_form_by_id(session, form_id)
    if not form:
        return None
    form.status = (
        FacebookLeadFormStatus.inactive.value
        if form.status == FacebookLeadFormStatus.active.value
        else FacebookLeadFormStatus.active.value
    )
    await session.flush()
    await session.refresh(form)
    return form


async def get_form_today_counts(session: AsyncSession, form_id: int) -> dict[str, int]:
    today = datetime.combine(datetime.utcnow().date(), time.min)
    base = select(func.count()).select_from(Lead).where(Lead.form_id == form_id, Lead.created_at >= today)
    leads = (await session.execute(base)).scalar_one()
    delivered = (
        await session.execute(
            base.where(Lead.status == LeadStatus.delivered.value)
        )
    ).scalar_one()
    errors = (
        await session.execute(
            base.where(Lead.status == LeadStatus.delivery_error.value)
        )
    ).scalar_one()
    return {"leads": int(leads), "delivered": int(delivered), "errors": int(errors)}
