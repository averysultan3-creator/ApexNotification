from __future__ import annotations
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lead import Lead
from app.models.client import Client
from app.utils.formatters import format_lead_card, load_json_list
from config import ADMIN_IDS, GOOGLE_SERVICE_ACCOUNT_JSON

logger = logging.getLogger(__name__)
_sheets_executor = ThreadPoolExecutor(max_workers=2)


async def deliver_lead(session: AsyncSession, bot: Bot | None, lead: Lead) -> None:
    client: Client | None = lead.client
    telegram_ok = False
    sheet_ok = False
    errors: list[str] = []

    text = format_lead_card(lead)

    # Send to admin
    if bot and ADMIN_IDS:
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, text)
                telegram_ok = True
            except Exception as e:
                logger.warning("admin tg %s: %s", admin_id, e)
                errors.append(f"admin:{admin_id}:{e}")

    # Send to client Telegram IDs
    if bot and client:
        for tid in load_json_list(client.telegram_ids_json):
            try:
                await bot.send_message(int(tid), text)
                telegram_ok = True
            except Exception as e:
                logger.warning("client tg %s tid %s: %s", client.id, tid, e)
                errors.append(f"client_tg:{tid}:{e}")

    # Google Sheet
    if client and client.google_sheet_id and GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            row = _build_row(lead, client)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                _sheets_executor,
                _append_sheet_sync,
                GOOGLE_SERVICE_ACCOUNT_JSON,
                client.google_sheet_id,
                client.google_sheet_name or "Sheet1",
                row,
            )
            sheet_ok = True
        except Exception as e:
            logger.error("sheets client %s: %s", client.id if client else "?", e)
            errors.append(f"sheet:{e}")

    if telegram_ok:
        lead.delivered_telegram = True
    if sheet_ok:
        lead.delivered_sheet = True
    lead.delivery_error = "; ".join(str(e)[:80] for e in errors[:3]) or None
    await session.flush()


def _build_row(lead: Lead, client: Client | None) -> list[Any]:
    from app.utils.formatters import fmt_dt
    return [
        fmt_dt(lead.created_at),
        client.name if client else "",
        lead.form.name if lead.form else "",
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
    except gspread.WorksheetNotFound:
        ws = sh.sheet1
    ws.append_row(row, value_input_option="USER_ENTERED")
