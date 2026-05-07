from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.lead import Lead
from models.offer import Offer
from models.lead_form import LeadForm
from models.referral_source import ReferralSource


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _count_leads(session: AsyncSession, **filters) -> int:
    q = select(func.count(Lead.id))
    conditions = []
    for key, val in filters.items():
        if val is not None:
            conditions.append(getattr(Lead, key) == val)
    if conditions:
        q = q.where(and_(*conditions))
    result = await session.execute(q)
    return result.scalar_one()


async def _count_leads_since(session: AsyncSession, since: datetime, **filters) -> int:
    q = select(func.count(Lead.id)).where(Lead.created_at >= since)
    conditions = []
    for key, val in filters.items():
        if val is not None:
            conditions.append(getattr(Lead, key) == val)
    if conditions:
        q = q.where(and_(*conditions))
    result = await session.execute(q)
    return result.scalar_one()


async def get_global_stats(session: AsyncSession) -> Dict[str, Any]:
    now = _now()
    total = await _count_leads(session)
    today = await _count_leads_since(session, now.replace(hour=0, minute=0, second=0))
    week = await _count_leads_since(session, now - timedelta(days=7))
    month = await _count_leads_since(session, now - timedelta(days=30))
    return {"total": total, "today": today, "week": week, "month": month}


async def get_client_stats(session: AsyncSession, client_id: int) -> Dict[str, Any]:
    now = _now()
    total = await _count_leads(session, client_id=client_id)
    today = await _count_leads_since(
        session, now.replace(hour=0, minute=0, second=0), client_id=client_id
    )
    week = await _count_leads_since(session, now - timedelta(days=7), client_id=client_id)
    month = await _count_leads_since(session, now - timedelta(days=30), client_id=client_id)

    # Best offers
    q = (
        select(Lead.offer_id, func.count(Lead.id).label("cnt"))
        .where(Lead.client_id == client_id)
        .group_by(Lead.offer_id)
        .order_by(func.count(Lead.id).desc())
        .limit(5)
    )
    rows = (await session.execute(q)).all()
    best_offers: List[Dict] = []
    for offer_id, cnt in rows:
        if offer_id:
            offer = await session.get(Offer, offer_id)
            best_offers.append({"name": offer.name if offer else "?", "count": cnt})

    # Best referral sources
    q2 = (
        select(Lead.referral_source_id, func.count(Lead.id).label("cnt"))
        .where(Lead.client_id == client_id)
        .group_by(Lead.referral_source_id)
        .order_by(func.count(Lead.id).desc())
        .limit(5)
    )
    rows2 = (await session.execute(q2)).all()
    best_refs: List[Dict] = []
    for ref_id, cnt in rows2:
        if ref_id:
            ref = await session.get(ReferralSource, ref_id)
            best_refs.append({"name": ref.name if ref else "?", "count": cnt})

    return {
        "total": total,
        "today": today,
        "week": week,
        "month": month,
        "best_offers": best_offers,
        "best_sources": best_refs,
    }


async def get_offer_stats(session: AsyncSession, offer_id: int) -> Dict[str, Any]:
    total = await _count_leads(session, offer_id=offer_id)

    # By form
    q = (
        select(Lead.form_id, func.count(Lead.id).label("cnt"))
        .where(Lead.offer_id == offer_id)
        .group_by(Lead.form_id)
        .order_by(func.count(Lead.id).desc())
    )
    rows = (await session.execute(q)).all()
    by_forms: List[Dict] = []
    for form_id, cnt in rows:
        if form_id:
            form = await session.get(LeadForm, form_id)
            by_forms.append({"name": form.name if form else "?", "count": cnt})

    # By source
    q2 = (
        select(Lead.referral_source_id, func.count(Lead.id).label("cnt"))
        .where(Lead.offer_id == offer_id)
        .group_by(Lead.referral_source_id)
        .order_by(func.count(Lead.id).desc())
    )
    rows2 = (await session.execute(q2)).all()
    by_sources: List[Dict] = []
    for ref_id, cnt in rows2:
        if ref_id:
            ref = await session.get(ReferralSource, ref_id)
            by_sources.append({"name": ref.name if ref else "?", "count": cnt})

    return {"total": total, "by_forms": by_forms, "by_sources": by_sources}


async def get_form_stats(session: AsyncSession, form_id: int) -> Dict[str, Any]:
    total_leads = await _count_leads(session, form_id=form_id)

    # By source
    q = (
        select(Lead.referral_source_id, func.count(Lead.id).label("cnt"))
        .where(Lead.form_id == form_id)
        .group_by(Lead.referral_source_id)
        .order_by(func.count(Lead.id).desc())
    )
    rows = (await session.execute(q)).all()
    by_sources: List[Dict] = []
    for ref_id, cnt in rows:
        name = "Прямая"
        if ref_id:
            ref = await session.get(ReferralSource, ref_id)
            name = ref.name if ref else "?"
        by_sources.append({"name": name, "count": cnt})

    # By status
    q2 = (
        select(Lead.status, func.count(Lead.id).label("cnt"))
        .where(Lead.form_id == form_id)
        .group_by(Lead.status)
    )
    rows2 = (await session.execute(q2)).all()
    by_status = {row[0]: row[1] for row in rows2}

    return {"total": total_leads, "by_sources": by_sources, "by_status": by_status}


async def get_ref_stats(session: AsyncSession, ref_id: int) -> Dict[str, Any]:
    total = await _count_leads(session, referral_source_id=ref_id)

    # Last lead date
    q = (
        select(func.max(Lead.created_at))
        .where(Lead.referral_source_id == ref_id)
    )
    last_date = (await session.execute(q)).scalar_one_or_none()

    # By status
    q2 = (
        select(Lead.status, func.count(Lead.id).label("cnt"))
        .where(Lead.referral_source_id == ref_id)
        .group_by(Lead.status)
    )
    rows = (await session.execute(q2)).all()
    by_status = {row[0]: row[1] for row in rows}

    return {"total": total, "last_lead_at": last_date, "by_status": by_status}
