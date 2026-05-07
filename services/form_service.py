import re
from typing import Optional, Tuple, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.lead_form import LeadForm, LeadFormStatus


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "_", slug)
    slug = slug.strip("_")
    return slug[:60] or "form"


async def _unique_slug(session: AsyncSession, base_slug: str) -> str:
    slug = base_slug
    counter = 1
    while True:
        result = await session.execute(select(LeadForm).where(LeadForm.slug == slug))
        if result.scalar_one_or_none() is None:
            return slug
        slug = f"{base_slug}_{counter}"
        counter += 1


async def get_forms_paginated(
    session: AsyncSession,
    page: int = 0,
    page_size: int = 10,
    client_id: Optional[int] = None,
    offer_id: Optional[int] = None,
    status_filter: Optional[str] = None,
) -> Tuple[List[LeadForm], int]:
    base_q = select(LeadForm)
    if client_id:
        base_q = base_q.where(LeadForm.client_id == client_id)
    if offer_id:
        base_q = base_q.where(LeadForm.offer_id == offer_id)
    if status_filter:
        base_q = base_q.where(LeadForm.status == status_filter)

    count_result = await session.execute(select(func.count()).select_from(base_q.subquery()))
    total = count_result.scalar_one()

    result = await session.execute(
        base_q.order_by(LeadForm.name).offset(page * page_size).limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_form_by_id(session: AsyncSession, form_id: int) -> Optional[LeadForm]:
    result = await session.execute(select(LeadForm).where(LeadForm.id == form_id))
    return result.scalar_one_or_none()


async def get_form_by_slug(session: AsyncSession, slug: str) -> Optional[LeadForm]:
    result = await session.execute(select(LeadForm).where(LeadForm.slug == slug))
    return result.scalar_one_or_none()


async def create_form(
    session: AsyncSession,
    client_id: int,
    offer_id: int,
    name: str,
    language: str = "ru",
    welcome_text: Optional[str] = None,
    success_text: Optional[str] = None,
    slug: Optional[str] = None,
) -> LeadForm:
    base_slug = _slugify(slug or name)
    unique = await _unique_slug(session, base_slug)
    form = LeadForm(
        client_id=client_id,
        offer_id=offer_id,
        name=name,
        slug=unique,
        language=language,
        welcome_text=welcome_text,
        success_text=success_text,
        status=LeadFormStatus.active.value,
    )
    session.add(form)
    await session.flush()
    await session.refresh(form)
    return form


async def update_form_field(
    session: AsyncSession, form_id: int, field: str, value: str
) -> Optional[LeadForm]:
    form = await get_form_by_id(session, form_id)
    if not form:
        return None
    allowed = {"name", "language", "welcome_text", "success_text"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' is not editable.")
    setattr(form, field, value if value else None)
    await session.flush()
    await session.refresh(form)
    return form


async def toggle_form_status(session: AsyncSession, form_id: int) -> Optional[LeadForm]:
    form = await get_form_by_id(session, form_id)
    if not form:
        return None
    form.status = (
        LeadFormStatus.inactive.value
        if form.status == LeadFormStatus.active.value
        else LeadFormStatus.active.value
    )
    await session.flush()
    await session.refresh(form)
    return form


async def delete_form(session: AsyncSession, form_id: int) -> bool:
    form = await get_form_by_id(session, form_id)
    if not form:
        return False
    await session.delete(form)
    await session.flush()
    return True
