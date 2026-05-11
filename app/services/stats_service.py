from __future__ import annotations
from datetime import datetime, date, timedelta
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lead import Lead
from app.models.preland_event import PrelandEvent, PrelandEventType


async def dashboard_today(session: AsyncSession) -> dict[str, Any]:
    today = date.today().isoformat()

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


async def funnel_stats_today(session: AsyncSession, funnel_form_id: int) -> dict[str, Any]:
    today = date.today().isoformat()

    leads = (await session.execute(
        select(func.count()).select_from(Lead).where(
            Lead.funnel_form_id == funnel_form_id,
            func.date(Lead.created_at) == today,
        )
    )).scalar() or 0

    delivered = (await session.execute(
        select(func.count()).select_from(Lead).where(
            Lead.funnel_form_id == funnel_form_id,
            func.date(Lead.created_at) == today,
            Lead.delivered_telegram == True,  # noqa: E712
        )
    )).scalar() or 0

    errors = (await session.execute(
        select(func.count()).select_from(Lead).where(
            Lead.funnel_form_id == funnel_form_id,
            func.date(Lead.created_at) == today,
            Lead.delivery_error.isnot(None),
        )
    )).scalar() or 0

    return {"leads_today": leads, "delivered_today": delivered, "errors_today": errors}


async def client_stats(
    session: AsyncSession,
    funnel_form_id: int,
    telegram_user_id: int,
) -> dict[str, Any]:
    """Stats visible to the client for their funnel."""
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    def _count_q(since: date | None = None, until: date | None = None):
        q = select(func.count()).select_from(Lead).where(
            Lead.funnel_form_id == funnel_form_id,
        )
        if since:
            q = q.where(func.date(Lead.created_at) >= since.isoformat())
        if until:
            q = q.where(func.date(Lead.created_at) <= until.isoformat())
        return q

    leads_today = (await session.execute(_count_q(today, today))).scalar() or 0
    leads_7d = (await session.execute(_count_q(week_ago))).scalar() or 0
    leads_30d = (await session.execute(_count_q(month_ago))).scalar() or 0

    last_lead_row = (await session.execute(
        select(Lead.created_at).where(Lead.funnel_form_id == funnel_form_id)
        .order_by(Lead.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    return {
        "leads_today": leads_today,
        "leads_7d": leads_7d,
        "leads_30d": leads_30d,
        "last_lead_at": last_lead_row,
    }


async def client_stats_by_day(
    session: AsyncSession,
    funnel_form_id: int,
    days: int = 7,
) -> list[dict[str, Any]]:
    """Returns list of {date, count} for last N days."""
    today = date.today()
    results = []
    for i in range(days):
        d = today - timedelta(days=i)
        cnt = (await session.execute(
            select(func.count()).select_from(Lead).where(
                Lead.funnel_form_id == funnel_form_id,
                func.date(Lead.created_at) == d.isoformat(),
            )
        )).scalar() or 0
        results.append({"date": d, "count": cnt})
    return results


async def client_stats_today_by_hour(
    session: AsyncSession,
    funnel_form_id: int,
) -> list[dict[str, Any]]:
    today = date.today().isoformat()
    all_leads = (await session.execute(
        select(Lead.created_at).where(
            Lead.funnel_form_id == funnel_form_id,
            func.date(Lead.created_at) == today,
        )
    )).scalars().all()

    by_hour: dict[int, int] = {}
    for dt in all_leads:
        h = dt.hour
        by_hour[h] = by_hour.get(h, 0) + 1

    return [{"hour": h, "count": c} for h, c in sorted(by_hour.items())]


async def leads_by_client(session: AsyncSession) -> list[dict[str, Any]]:
    """Count leads delivered to each recipient (via LeadDeliveryHistory)."""
    from app.models.client_recipient import ClientRecipient
    from app.models.lead_delivery_history import LeadDeliveryHistory
    rows = (await session.execute(
        select(
            ClientRecipient.first_name,
            ClientRecipient.telegram_username,
            func.count(LeadDeliveryHistory.id).label("cnt"),
        )
        .outerjoin(
            LeadDeliveryHistory,
            LeadDeliveryHistory.recipient_telegram_id == ClientRecipient.telegram_user_id,
        )
        .group_by(ClientRecipient.id)
        .order_by(func.count(LeadDeliveryHistory.id).desc())
    )).all()
    return [
        {"client": r.first_name or r.telegram_username or "Unknown", "count": r.cnt}
        for r in rows
    ]


async def leads_by_form(session: AsyncSession) -> list[dict[str, Any]]:
    from app.models.funnel_form import FunnelForm
    rows = (await session.execute(
        select(FunnelForm.form_name, func.count(Lead.id).label("cnt"))
        .outerjoin(Lead, Lead.funnel_form_id == FunnelForm.id)
        .group_by(FunnelForm.id, FunnelForm.form_name)
        .order_by(func.count(Lead.id).desc())
    )).all()
    return [{"form": r.form_name, "count": r.cnt} for r in rows]


async def preland_stats_today(session: AsyncSession) -> list[dict[str, Any]]:
    from app.models.preland import Preland
    today = date.today().isoformat()
    rows = (await session.execute(
        select(
            Preland.slug,
            func.count(PrelandEvent.id).filter(
                PrelandEvent.event_type == PrelandEventType.page_view.value
            ).label("views"),
            func.count(PrelandEvent.id).filter(
                PrelandEvent.event_type == PrelandEventType.button_click.value
            ).label("clicks"),
        )
        .outerjoin(
            PrelandEvent,
            (PrelandEvent.preland_id == Preland.id)
            & (func.date(PrelandEvent.created_at) == today),
        )
        .group_by(Preland.id, Preland.slug)
    )).all()
    result = []
    for r in rows:
        ctr = round(r.clicks / r.views * 100, 1) if r.views else 0.0
        result.append({"name": r.slug, "views": r.views, "clicks": r.clicks, "ctr": ctr})
    return result
