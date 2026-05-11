from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client_recipient import ClientRecipient, RecipientStatus
from app.models.funnel_form import FunnelForm
from app.models.lead import Lead
from app.models.lead_delivery_history import (
    DeliveryStatus,
    DeliveryType,
    LeadDeliveryHistory,
)
from app.services.admin_alert_service import notify_admins
from app.services.funnel_form_service import get_form_by_id
from app.utils.formatters import format_lead_for_client

logger = logging.getLogger(__name__)


_HANDLE_COL_KEYWORDS = [
    "telegram", "tg", "ник", "nick", "нік", "handle",
    "username", "instagram", "insta", "ig", "соц",
]


def _find_handle_in_raw(raw: dict) -> str:
    """
    Scan all columns in raw payload.
    Priority 1: column name contains telegram/tg/nick/handle keywords.
    Priority 2: any cell value that looks like @handle or t.me/xxx.
    """
    import re
    fallback = ""
    for col, val in raw.items():
        if not val:
            continue
        cell = str(val).strip()
        col_lower = str(col).lower()
        # Priority 1: column name matches
        if any(kw in col_lower for kw in _HANDLE_COL_KEYWORDS):
            if cell:
                return cell
        # Priority 2: value looks like a handle
        if not fallback:
            if re.match(r'^@[a-zA-Z0-9_.]{2,}', cell) or re.search(r't\.me/', cell, re.IGNORECASE):
                fallback = cell
    return fallback


async def handle_google_sheet_lead(
    session: AsyncSession,
    bot: Bot | None,
    payload: dict,
) -> dict:
    """
    POST /api/google-sheet/lead handler.
    Admin does not receive a Telegram message for every normal lead.
    Admin is alerted only when delivery is broken or there are no recipients.
    """
    try:
        return await _process(session, bot, payload)
    except Exception as e:
        logger.exception("google_sheet_lead unhandled: %s", e)
        try:
            await notify_admins(
                session,
                bot,
                f"Google Sheet lead endpoint failed.\n\nError: <code>{str(e)[:300]}</code>",
            )
        except Exception:
            logger.exception("failed to send admin alert for google_sheet_lead")
        return {"ok": False, "error": "internal_error"}


async def _process(session: AsyncSession, bot: Bot | None, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "invalid_payload"}

    funnel_id = payload.get("funnel_id")
    secret = payload.get("secret")
    external_lead_id = str(payload.get("external_lead_id") or "").strip()

    if not funnel_id or not secret or not external_lead_id:
        return {"ok": False, "error": "missing_fields"}

    try:
        funnel_pk = int(funnel_id)
    except (TypeError, ValueError):
        return {"ok": False, "error": "invalid_funnel_id"}

    funnel = await get_form_by_id(session, funnel_pk)
    if not funnel:
        return {"ok": False, "error": "funnel_not_found"}

    if funnel.join_code != secret:
        logger.warning("bad secret for funnel %s", funnel_id)
        return {"ok": False, "error": "invalid_secret"}

    if funnel.status != "active":
        return {"ok": False, "error": "funnel_paused"}

    existing = (
        await session.execute(
            select(Lead).where(
                Lead.funnel_form_id == funnel.id,
                Lead.external_lead_id == external_lead_id,
            )
        )
    ).scalar_one_or_none()

    if existing:
        logger.info("duplicate lead funnel=%s external=%s", funnel.id, external_lead_id)
        return {"ok": True, "duplicate": True, "lead_id": existing.id}

    lead_created_time: datetime | None = None
    raw_lct = payload.get("lead_created_time")
    if raw_lct:
        try:
            lead_created_time = datetime.fromisoformat(str(raw_lct).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    raw_data = payload.get("raw") or {}

    # Extract telegram from payload; fallback to scanning raw columns
    _telegram = str(payload.get("telegram") or "").strip() or _find_handle_in_raw(raw_data)

    # Clean phone prefix added by some FB/GSheet exports ("p:", "ph:", "tel:")
    _phone = str(payload.get("phone") or "").strip()
    import re as _re
    _phone = _re.sub(r'^(p:|ph:|tel:)', '', _phone, flags=_re.IGNORECASE).strip() or None

    lead = Lead(
        funnel_form_id=funnel.id,
        external_lead_id=external_lead_id,
        fb_lead_id=None,
        fb_form_id=str(payload.get("fb_form_id") or ""),
        form_name=str(payload.get("form_name") or "") or funnel.form_name,
        full_name=str(payload.get("full_name") or "") or None,
        phone=_phone,
        email=str(payload.get("email") or "") or None,
        telegram=_telegram or None,
        tag=funnel.tag,
        lead_created_time=lead_created_time,
        raw_data_json=json.dumps(raw_data, ensure_ascii=False),
        delivered_admin=False,
        delivered_telegram=False,
        delivered_clients=False,
        delivered_recipients_count=0,
    )

    try:
        session.add(lead)
        await session.flush()
        await session.refresh(lead)
    except IntegrityError:
        await session.rollback()
        existing = (
            await session.execute(
                select(Lead).where(
                    Lead.funnel_form_id == funnel_pk,
                    Lead.external_lead_id == external_lead_id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            return {"ok": True, "duplicate": True, "lead_id": existing.id}
        raise

    recipients = (
        await session.execute(
            select(ClientRecipient).where(
                ClientRecipient.funnel_form_id == funnel.id,
                ClientRecipient.status == RecipientStatus.active.value,
            )
        )
    ).scalars().all()

    if not recipients:
        await notify_admins(
            session,
            bot,
            (
                f"Lead #{lead.id} was saved, but funnel has no active recipients.\n\n"
                f"Funnel: <b>{funnel.form_name}</b>\n"
                f"Tag: {funnel.tag or '-'}\n"
                f"Name: {lead.full_name or '-'}\n"
                f"Phone: {lead.phone or '-'}"
            ),
        )

    errors: list[str] = []
    recipients_ok = 0
    text_client = format_lead_for_client(lead)

    for recipient in recipients:
        status = DeliveryStatus.failed.value
        err_msg: str | None = None
        if bot:
            try:
                await bot.send_message(recipient.telegram_user_id, text_client)
                status = DeliveryStatus.sent.value
                recipients_ok += 1
            except Exception as e:
                logger.warning("recipient tg %s: %s", recipient.telegram_user_id, e)
                err_msg = str(e)[:200]
                errors.append(f"recip:{recipient.telegram_user_id}:{e}")

        session.add(
            LeadDeliveryHistory(
                lead_id=lead.id,
                recipient_telegram_id=recipient.telegram_user_id,
                delivery_type=DeliveryType.new.value,
                status=status,
                error_message=err_msg,
            )
        )

    lead.delivered_clients = recipients_ok > 0
    lead.delivered_telegram = recipients_ok > 0
    lead.delivered_recipients_count = recipients_ok
    lead.delivery_error = "; ".join(str(e)[:80] for e in errors[:3]) or None

    await session.flush()

    logger.info(
        "lead saved funnel=%s id=%s name=%r recipients_ok=%d errors=%d",
        funnel.id, lead.id, lead.full_name, recipients_ok, len(errors),
    )

    if errors:
        err_preview = errors[0][:180]
        await notify_admins(
            session,
            bot,
            (
                f"Lead #{lead.id} delivery failed.\n\n"
                f"Funnel: <b>{funnel.form_name}</b>\n"
                f"Tag: {funnel.tag or '-'}\n"
                f"Error: <code>{err_preview}</code>\n\n"
                f"Open bot: <b>Leads -> Errors</b>"
            ),
        )

    return {"ok": True, "lead_id": lead.id}


async def send_old_leads_to_recipient(
    session: AsyncSession,
    bot: Bot,
    recipient: ClientRecipient,
    leads: list[Lead],
    *,
    force: bool = False,
    delay: float = 0.2,
) -> tuple[int, int]:
    """
    Send old leads to a single recipient.
    Skips leads already delivered unless force=True.
    Returns (sent_count, skipped_or_error_count).
    """
    sent = 0
    skipped = 0

    for lead in leads:
        if not force:
            already = (
                await session.execute(
                    select(LeadDeliveryHistory).where(
                        LeadDeliveryHistory.lead_id == lead.id,
                        LeadDeliveryHistory.recipient_telegram_id == recipient.telegram_user_id,
                        LeadDeliveryHistory.status == DeliveryStatus.sent.value,
                    )
                )
            ).scalar_one_or_none()
            if already:
                skipped += 1
                continue

        text = format_lead_for_client(lead, is_archive=True)
        err_msg: str | None = None
        status = DeliveryStatus.failed.value
        try:
            await bot.send_message(recipient.telegram_user_id, text)
            status = DeliveryStatus.sent.value
            sent += 1
        except Exception as e:
            logger.warning("backfill lead=%s recip=%s: %s", lead.id, recipient.id, e)
            err_msg = str(e)[:200]
            skipped += 1

        existing_log = (
            await session.execute(
                select(LeadDeliveryHistory).where(
                    LeadDeliveryHistory.lead_id == lead.id,
                    LeadDeliveryHistory.recipient_telegram_id == recipient.telegram_user_id,
                    LeadDeliveryHistory.delivery_type == DeliveryType.backfill.value,
                )
            )
        ).scalar_one_or_none()

        if existing_log:
            existing_log.status = status
            existing_log.error_message = err_msg
        else:
            session.add(
                LeadDeliveryHistory(
                    lead_id=lead.id,
                    recipient_telegram_id=recipient.telegram_user_id,
                    delivery_type=DeliveryType.backfill.value,
                    status=status,
                    error_message=err_msg,
                )
            )

        if delay:
            await asyncio.sleep(delay)

    await session.flush()
    return sent, skipped
