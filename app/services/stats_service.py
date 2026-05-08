from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery_log import DeliveryLog, DeliveryStatus
from app.models.facebook_lead_form import FacebookLeadForm
from app.models.lead import Lead
from app.models.preland import Preland
from app.models.preland_event import PrelandEvent, PrelandEventType
from app.utils.formatters import percent


def _today_start() -> datetime:
    return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)


async def dashboard_today(session: AsyncSession) -> dict[str, Any]:
    today = _today_start()
    leads_today = int((await session.execute(select(func.count()).select_from(Lead).where(Lead.created_at >= today))).scalar_one())
    delivered_today = int(
        (
            await session.execute(
                select(func.count()).select_from(Lead).where(
                    Lead.created_at >= today,
                    (Lead.delivered_telegram.is_(True)) | (Lead.delivered_email.is_(True)) | (Lead.delivered_sheet.is_(True)),
                )
            )
        ).scalar_one()
    )
    delivery_errors_today = int(
        (
            await session.execute(
                select(func.count()).select_from(DeliveryLog).where(
                    DeliveryLog.created_at >= today,
                    DeliveryLog.status == DeliveryStatus.error.value,
                )
            )
        ).scalar_one()
    )
    visits = int(
        (
            await session.execute(
                select(func.count()).select_from(PrelandEvent).where(
                    PrelandEvent.created_at >= today,
                    PrelandEvent.event_type == PrelandEventType.page_view.value,
                )
            )
        ).scalar_one()
    )
    clicks = int(
        (
            await session.execute(
                select(func.count()).select_from(PrelandEvent).where(
                    PrelandEvent.created_at >= today,
                    PrelandEvent.event_type == PrelandEventType.button_click.value,
                )
            )
        ).scalar_one()
    )
    return {
        "leads_today": leads_today,
        "delivered_today": delivered_today,
        "delivery_errors_today": delivery_errors_today,
        "preland_visits_today": visits,
        "preland_clicks_today": clicks,
        "preland_ctr_today": percent(clicks, visits),
    }


async def leads_by_client(session: AsyncSession) -> list[tuple[str, int]]:
    stmt = (
        select(Lead.client_id, func.count())
        .group_by(Lead.client_id)
        .order_by(func.count().desc())
    )
    rows = (await session.execute(stmt)).all()
    return [(str(client_id or "-"), int(count)) for client_id, count in rows]


async def leads_by_facebook_form(session: AsyncSession) -> list[tuple[str, int]]:
    stmt = (
        select(FacebookLeadForm.name, func.count(Lead.id))
        .join(Lead, Lead.form_id == FacebookLeadForm.id, isouter=True)
        .group_by(FacebookLeadForm.id)
        .order_by(func.count(Lead.id).desc())
    )
    return [(name, int(count)) for name, count in (await session.execute(stmt)).all()]


async def delivery_errors(session: AsyncSession, limit: int = 20) -> list[DeliveryLog]:
    stmt = (
        select(DeliveryLog)
        .where(DeliveryLog.status == DeliveryStatus.error.value)
        .order_by(DeliveryLog.created_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def preland_visits_clicks_ctr(session: AsyncSession, days: int = 1) -> dict[str, Any]:
    date_from = _today_start() if days <= 1 else datetime.utcnow() - timedelta(days=days)
    visits = int(
        (
            await session.execute(
                select(func.count()).select_from(PrelandEvent).where(
                    PrelandEvent.created_at >= date_from,
                    PrelandEvent.event_type == PrelandEventType.page_view.value,
                )
            )
        ).scalar_one()
    )
    clicks = int(
        (
            await session.execute(
                select(func.count()).select_from(PrelandEvent).where(
                    PrelandEvent.created_at >= date_from,
                    PrelandEvent.event_type == PrelandEventType.button_click.value,
                )
            )
        ).scalar_one()
    )
    prelands = int((await session.execute(select(func.count()).select_from(Preland))).scalar_one())
    return {"prelands": prelands, "visits": visits, "clicks": clicks, "ctr": percent(clicks, visits)}


async def preland_stats_by_day(session: AsyncSession, days: int = 7) -> list[dict[str, Any]]:
    """Visits / clicks / CTR сгруппированные по дням за последние N дней."""
    date_from = datetime.utcnow() - timedelta(days=days)
    day_col = func.strftime("%Y-%m-%d", PrelandEvent.created_at).label("day")

    visits_q = (
        select(day_col, func.count().label("cnt"))
        .where(
            PrelandEvent.created_at >= date_from,
            PrelandEvent.event_type == PrelandEventType.page_view.value,
        )
        .group_by("day")
        .order_by("day")
    )
    clicks_q = (
        select(day_col, func.count().label("cnt"))
        .where(
            PrelandEvent.created_at >= date_from,
            PrelandEvent.event_type == PrelandEventType.button_click.value,
        )
        .group_by("day")
        .order_by("day")
    )
    visits_map = {row.day: row.cnt for row in (await session.execute(visits_q)).all()}
    clicks_map = {row.day: row.cnt for row in (await session.execute(clicks_q)).all()}

    all_days = sorted(set(list(visits_map) + list(clicks_map)))
    result = []
    for day in all_days:
        v = visits_map.get(day, 0)
        c = clicks_map.get(day, 0)
        result.append({"day": day, "visits": v, "clicks": c, "ctr": percent(c, v)})
    return result


async def preland_stats_by_hour(session: AsyncSession) -> list[dict[str, Any]]:
    """Visits / clicks по часам за сегодня (UTC)."""
    today = _today_start()
    hour_col = func.strftime("%H", PrelandEvent.created_at).label("hour")

    visits_q = (
        select(hour_col, func.count().label("cnt"))
        .where(
            PrelandEvent.created_at >= today,
            PrelandEvent.event_type == PrelandEventType.page_view.value,
        )
        .group_by("hour")
        .order_by("hour")
    )
    clicks_q = (
        select(hour_col, func.count().label("cnt"))
        .where(
            PrelandEvent.created_at >= today,
            PrelandEvent.event_type == PrelandEventType.button_click.value,
        )
        .group_by("hour")
        .order_by("hour")
    )
    visits_map = {row.hour: row.cnt for row in (await session.execute(visits_q)).all()}
    clicks_map = {row.hour: row.cnt for row in (await session.execute(clicks_q)).all()}

    result = []
    for h in range(24):
        hh = f"{h:02d}"
        v = visits_map.get(hh, 0)
        c = clicks_map.get(hh, 0)
        if v or c:
            result.append({"hour": f"{hh}:00", "visits": v, "clicks": c, "ctr": percent(c, v)})
    return result


async def leads_stats_by_day(session: AsyncSession, days: int = 7) -> list[dict[str, Any]]:
    """Лиды сгруппированные по дням за N дней."""
    date_from = datetime.utcnow() - timedelta(days=days)
    from app.models.client import Client
    day_col = func.strftime("%Y-%m-%d", Lead.created_at).label("day")
    stmt = (
        select(day_col, func.count(Lead.id).label("cnt"))
        .where(Lead.created_at >= date_from)
        .group_by("day")
        .order_by("day")
    )
    rows = (await session.execute(stmt)).all()
    return [{"day": row.day, "leads": row.cnt} for row in rows]
