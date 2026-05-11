from __future__ import annotations
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.lead import Lead
from app.models.funnel_form import FunnelForm
from app.models.lead_delivery_history import LeadDeliveryHistory, DeliveryStatus, DeliveryType
from app.utils.formatters import format_lead_card, format_lead_notification
from config import ADMIN_IDS, GOOGLE_SERVICE_ACCOUNT_JSON

logger = logging.getLogger(__name__)
_sheets_executor = ThreadPoolExecutor(max_workers=2)


async def deliver_lead(session: AsyncSession, bot: Bot | None, lead: Lead) -> None:
    funnel: FunnelForm | None = await _load_funnel(session, lead)
    errors: list[str] = []
    admin_ok = False
    clients_ok = False
    sheet_ok = False
    recipients_ok = 0

    text_admin = format_lead_card(lead)
    text_client = format_lead_notification(lead)

    # Admin notification
    if bot and ADMIN_IDS:
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, text_admin)
                admin_ok = True
            except Exception as e:
                logger.warning("admin tg %s: %s", admin_id, e)
                errors.append(f"admin:{admin_id}:{e}")

    # Client recipients
    if bot and funnel and funnel.recipients:
        for recipient in funnel.recipients:
            if recipient.status != "active":
                continue
            status = DeliveryStatus.failed.value
            err_msg: str | None = None
            try:
                await bot.send_message(recipient.telegram_user_id, text_client)
                clients_ok = True
                recipients_ok += 1
                status = DeliveryStatus.sent.value
            except Exception as e:
                logger.warning("client tg %s: %s", recipient.telegram_user_id, e)
                err_msg = str(e)[:200]
                errors.append(f"client:{recipient.telegram_user_id}:{e}")
            await _upsert_history(
                session,
                lead_id=lead.id,
                recipient_telegram_id=recipient.telegram_user_id,
                delivery_type=DeliveryType.new.value,
                status=status,
                error_message=err_msg,
            )

    # Google Sheets
    if funnel and funnel.google_sheet_id and GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            row = _build_row(lead, funnel)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                _sheets_executor,
                _append_sheet_sync,
                GOOGLE_SERVICE_ACCOUNT_JSON,
                funnel.google_sheet_id,
                funnel.google_sheet_name or "Leads",
                row,
            )
            sheet_ok = True
        except Exception as e:
            logger.error("sheets funnel %s: %s", funnel.id if funnel else "?", e)
            errors.append(f"sheet:{e}")

    lead.delivered_admin = admin_ok
    lead.delivered_telegram = clients_ok
    lead.delivered_clients = clients_ok
    lead.delivered_recipients_count = recipients_ok
    lead.delivered_sheet = sheet_ok
    lead.delivery_error = "; ".join(str(e)[:80] for e in errors[:3]) or None
    await session.flush()


async def _load_funnel(session: AsyncSession, lead: Lead) -> FunnelForm | None:
    if not lead.funnel_form_id:
        return None
    return (await session.execute(
        select(FunnelForm)
        .options(selectinload(FunnelForm.recipients))
        .where(FunnelForm.id == lead.funnel_form_id)
        .execution_options(populate_existing=True)
    )).scalar_one_or_none()


async def _upsert_history(
    session: AsyncSession,
    *,
    lead_id: int,
    recipient_telegram_id: int,
    delivery_type: str,
    status: str,
    error_message: str | None,
) -> None:
    existing = (await session.execute(
        select(LeadDeliveryHistory).where(
            LeadDeliveryHistory.lead_id == lead_id,
            LeadDeliveryHistory.recipient_telegram_id == recipient_telegram_id,
            LeadDeliveryHistory.delivery_type == delivery_type,
        )
    )).scalar_one_or_none()
    if existing:
        existing.status = status
        existing.error_message = error_message
    else:
        session.add(LeadDeliveryHistory(
            lead_id=lead_id,
            recipient_telegram_id=recipient_telegram_id,
            delivery_type=delivery_type,
            status=status,
            error_message=error_message,
        ))


def _build_row(lead: Lead, funnel: FunnelForm | None) -> list[Any]:
    from app.utils.formatters import fmt_dt
    return [
        fmt_dt(lead.created_at),
        funnel.form_name if funnel else "",
        funnel.tag if funnel else "",
        lead.full_name or "",
        lead.phone or "",
        lead.email or "",
        lead.external_lead_id or lead.fb_lead_id or "",
        str(lead.id),
    ]


def _append_sheet_sync(creds_json: str, sheet_id: str, sheet_name: str, row: list) -> None:
    import gspread
    from google.oauth2.service_account import Credentials
    try:
        data = json.loads(creds_json)
    except (json.JSONDecodeError, ValueError):
        with open(creds_json) as f:
            data = json.load(f)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(data, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(sheet_name)
    except Exception:
        ws = sh.get_worksheet(0)
    ws.append_row(row, value_input_option="USER_ENTERED")
