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
