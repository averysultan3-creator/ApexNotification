from __future__ import annotations
from datetime import datetime
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lead import Lead
from app.models.preland_event import PrelandEvent, PrelandEventType


async def dashboard_today(session: AsyncSession) -> dict[str, Any]:
    today = datetime.now().date().isoformat()

    leads = (await session.execute(
        select(func.count()).select_from(Lead).where(func.date(Lead.created_at) == today)
    )).scalar() or 0

    delivered = (await session.execute(
        select(func.count()).select_from(Lead).where(
            func.date(Lead.created_at) == today,
            Lead.delivered_telegram == True,  # noqa: E712
        )
    )).scalar() or 0

    errors = (await session.execute(
        select(func.count()).select_from(Lead).where(
            func.date(Lead.created_at) == today,
            Lead.delivery_error.isnot(None),
        )
    )).scalar() or 0

    views = (await session.execute(
        select(func.count()).select_from(PrelandEvent).where(
            func.date(PrelandEvent.created_at) == today,
            PrelandEvent.event_type == PrelandEventType.page_view.value,
        )
    )).scalar() or 0

    clicks = (await session.execute(
        select(func.count()).select_from(PrelandEvent).where(
            func.date(PrelandEvent.created_at) == today,
            PrelandEvent.event_type == PrelandEventType.button_click.value,
        )
    )).scalar() or 0

    ctr = round(clicks / views * 100, 1) if views else 0.0

    return {
        "leads_today": leads,
        "delivered_today": delivered,
        "delivery_errors_today": errors,
        "preland_visits_today": views,
        "preland_clicks_today": clicks,
        "preland_ctr_today": ctr,
    }


async def leads_by_form(session: AsyncSession) -> list[dict[str, Any]]:
    from app.models.facebook_lead_form import FacebookLeadForm
    rows = (await session.execute(
        select(FacebookLeadForm.name, func.count(Lead.id).label("cnt"))
        .join(Lead, Lead.facebook_form_id == FacebookLeadForm.id, isouter=True)
        .group_by(FacebookLeadForm.id, FacebookLeadForm.name)
        .order_by(func.count(Lead.id).desc())
    )).all()
    return [{"form": r.name, "count": r.cnt} for r in rows]


async def leads_by_client(session: AsyncSession) -> list[dict[str, Any]]:
    from app.models.client import Client
    rows = (await session.execute(
        select(Client.name, func.count(Lead.id).label("cnt"))
        .join(Lead, Lead.client_id == Client.id, isouter=True)
        .group_by(Client.id, Client.name)
        .order_by(func.count(Lead.id).desc())
    )).all()
    return [{"client": r.name, "count": r.cnt} for r in rows]


async def preland_stats_today(session: AsyncSession) -> list[dict[str, Any]]:
    from app.models.preland import Preland
    today = datetime.now().date().isoformat()
    prelands = (await session.execute(select(Preland))).scalars().all()
    result = []
    for p in prelands:
        v = (await session.execute(
            select(func.count()).select_from(PrelandEvent).where(
                PrelandEvent.preland_id == p.id,
                PrelandEvent.event_type == PrelandEventType.page_view.value,
                func.date(PrelandEvent.created_at) == today,
            )
        )).scalar() or 0
        c = (await session.execute(
            select(func.count()).select_from(PrelandEvent).where(
                PrelandEvent.preland_id == p.id,
                PrelandEvent.event_type == PrelandEventType.button_click.value,
                func.date(PrelandEvent.created_at) == today,
            )
        )).scalar() or 0
        result.append({
            "name": p.name, "slug": p.slug,
            "views": v, "clicks": c,
            "ctr": round(c / v * 100, 1) if v else 0.0,
        })
    return result
