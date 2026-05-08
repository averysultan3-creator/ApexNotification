from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.facebook_lead_form import FacebookLeadForm, FacebookLeadFormStatus


async def create_form(
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
    )
    session.add(form)
    await session.flush()
    await session.refresh(form)
    return form


async def get_form_by_id(session: AsyncSession, form_id: int) -> FacebookLeadForm | None:
    return (await session.execute(
        select(FacebookLeadForm).where(FacebookLeadForm.id == form_id)
    )).scalar_one_or_none()


async def get_form_by_fb_form_id(session: AsyncSession, fb_form_id: str) -> FacebookLeadForm | None:
    return (await session.execute(
        select(FacebookLeadForm).where(FacebookLeadForm.fb_form_id == fb_form_id)
    )).scalar_one_or_none()


async def list_forms(session: AsyncSession, active_only: bool = False) -> list[FacebookLeadForm]:
    stmt = select(FacebookLeadForm).order_by(FacebookLeadForm.created_at.desc())
    if active_only:
        stmt = stmt.where(FacebookLeadForm.status == FacebookLeadFormStatus.active.value)
    return list((await session.execute(stmt)).scalars().all())


async def toggle_form_status(session: AsyncSession, form_id: int) -> FacebookLeadForm | None:
    form = await get_form_by_id(session, form_id)
    if not form:
        return None
    form.status = (
        FacebookLeadFormStatus.inactive.value
        if form.status == FacebookLeadFormStatus.active.value
        else FacebookLeadFormStatus.active.value
    )
    await session.flush()
    return form
