from __future__ import annotations
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lead import Lead
from app.models.funnel_form import FunnelForm
from app.utils.formatters import format_lead_card, format_lead_notification
from config import ADMIN_IDS, GOOGLE_SERVICE_ACCOUNT_JSON

logger = logging.getLogger(__name__)
_sheets_executor = ThreadPoolExecutor(max_workers=2)


async def deliver_lead(session: AsyncSession, bot: Bot | None, lead: Lead) -> None:
    funnel: FunnelForm | None = lead.funnel_form
    errors: list[str] = []
    admin_ok = False
    clients_ok = False
    sheet_ok = False

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
            try:
                await bot.send_message(recipient.telegram_user_id, text_client)
                clients_ok = True
            except Exception as e:
                logger.warning("client tg %s: %s", recipient.telegram_user_id, e)
                errors.append(f"client:{recipient.telegram_user_id}:{e}")

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
    lead.delivered_clients = clients_ok
    lead.delivered_sheet = sheet_ok
    lead.delivery_error = "; ".join(str(e)[:80] for e in errors[:3]) or None
    await session.flush()


def _build_row(lead: Lead, funnel: FunnelForm | None) -> list[Any]:
    from app.utils.formatters import fmt_dt
    return [
        fmt_dt(lead.created_at),
        funnel.form_name if funnel else "",
        funnel.tag if funnel else "",
        lead.full_name or "",
        lead.phone or "",
        lead.email or "",
        lead.fb_lead_id or "",
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
