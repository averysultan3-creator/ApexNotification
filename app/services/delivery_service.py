from __future__ import annotations

import asyncio
import json
import smtplib
from email.message import EmailMessage
from typing import Iterable

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery_log import DeliveryChannel, DeliveryLog, DeliveryStatus
from app.models.delivery_rule import DeliveryRule, DeliveryRuleStatus
from app.models.lead import Lead, SourceType
from app.services.lead_service import get_lead_by_id, mark_lead_delivery_state
from app.utils.formatters import format_lead_card, load_json_list
from config import (
    ADMIN_IDS,
    EMAIL_ENABLED,
    GOOGLE_SHEETS_ENABLED,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
)


async def create_delivery_rule(
    session: AsyncSession,
    *,
    source_type: str,
    source_id: int,
    client_id: int,
    send_to_admin: bool = True,
    telegram_ids: list[int | str] | None = None,
    emails: list[str] | None = None,
    google_sheet_id: str | None = None,
) -> DeliveryRule:
    existing = await get_delivery_rule(session, source_type, source_id, active_only=False)
    if existing:
        existing.client_id = client_id
        existing.send_to_admin = send_to_admin
        existing.telegram_ids_json = json.dumps([str(item) for item in (telegram_ids or [])], ensure_ascii=False)
        existing.emails_json = json.dumps([item.strip() for item in (emails or []) if item.strip()], ensure_ascii=False)
        existing.google_sheet_id = google_sheet_id or None
        existing.status = DeliveryRuleStatus.active.value
        await session.flush()
        await session.refresh(existing)
        return existing

    rule = DeliveryRule(
        source_type=source_type,
        source_id=source_id,
        client_id=client_id,
        send_to_admin=send_to_admin,
        telegram_ids_json=json.dumps([str(item) for item in (telegram_ids or [])], ensure_ascii=False),
        emails_json=json.dumps([item.strip() for item in (emails or []) if item.strip()], ensure_ascii=False),
        google_sheet_id=google_sheet_id or None,
        status=DeliveryRuleStatus.active.value,
    )
    session.add(rule)
    await session.flush()
    await session.refresh(rule)
    return rule


async def get_delivery_rule(
    session: AsyncSession,
    source_type: str,
    source_id: int,
    *,
    active_only: bool = True,
) -> DeliveryRule | None:
    stmt = select(DeliveryRule).where(DeliveryRule.source_type == source_type, DeliveryRule.source_id == source_id)
    if active_only:
        stmt = stmt.where(DeliveryRule.status == DeliveryRuleStatus.active.value)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_delivery_rules(session: AsyncSession) -> list[DeliveryRule]:
    stmt = select(DeliveryRule).order_by(DeliveryRule.created_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def create_delivery_log(
    session: AsyncSession,
    *,
    lead_id: int,
    channel: str,
    recipient: str | None,
    status: str,
    error_message: str | None = None,
) -> DeliveryLog:
    log = DeliveryLog(
        lead_id=lead_id,
        channel=channel,
        recipient=recipient,
        status=status,
        error_message=error_message,
    )
    session.add(log)
    await session.flush()
    return log


async def send_lead_to_admin(session: AsyncSession, bot: Bot | None, lead: Lead) -> tuple[bool, bool]:
    return await _send_telegram_many(
        session,
        bot,
        lead,
        channel=DeliveryChannel.admin_telegram.value,
        recipients=[str(item) for item in ADMIN_IDS],
    )


async def send_lead_to_telegram(session: AsyncSession, bot: Bot | None, lead: Lead, telegram_id: int | str) -> bool:
    success, _ = await _send_telegram_many(
        session,
        bot,
        lead,
        channel=DeliveryChannel.client_telegram.value,
        recipients=[str(telegram_id)],
    )
    return success


async def _send_telegram_many(
    session: AsyncSession,
    bot: Bot | None,
    lead: Lead,
    *,
    channel: str,
    recipients: Iterable[str],
) -> tuple[bool, bool]:
    any_success = False
    any_error = False
    text = format_lead_card(lead)
    for recipient in recipients:
        if not recipient:
            continue
        if bot is None:
            await create_delivery_log(
                session,
                lead_id=lead.id,
                channel=channel,
                recipient=recipient,
                status=DeliveryStatus.skipped.value,
                error_message="Bot instance is not configured for this web process.",
            )
            continue
        try:
            await bot.send_message(chat_id=int(recipient), text=text)
            await create_delivery_log(
                session,
                lead_id=lead.id,
                channel=channel,
                recipient=recipient,
                status=DeliveryStatus.success.value,
            )
            any_success = True
        except Exception as exc:
            await create_delivery_log(
                session,
                lead_id=lead.id,
                channel=channel,
                recipient=recipient,
                status=DeliveryStatus.error.value,
                error_message=str(exc),
            )
            any_error = True
    return any_success, any_error


async def send_lead_to_email(session: AsyncSession, lead: Lead, email: str) -> bool:
    if not EMAIL_ENABLED:
        await create_delivery_log(
            session,
            lead_id=lead.id,
            channel=DeliveryChannel.email.value,
            recipient=email,
            status=DeliveryStatus.skipped.value,
            error_message="EMAIL_ENABLED=false",
        )
        return False
    try:
        await asyncio.to_thread(_send_email_sync, lead, email)
        await create_delivery_log(
            session,
            lead_id=lead.id,
            channel=DeliveryChannel.email.value,
            recipient=email,
            status=DeliveryStatus.success.value,
        )
        return True
    except Exception as exc:
        await create_delivery_log(
            session,
            lead_id=lead.id,
            channel=DeliveryChannel.email.value,
            recipient=email,
            status=DeliveryStatus.error.value,
            error_message=str(exc),
        )
        return False


def _send_email_sync(lead: Lead, recipient: str) -> None:
    if not SMTP_USERNAME or not SMTP_PASSWORD or not SMTP_FROM:
        raise RuntimeError("SMTP credentials are incomplete.")
    msg = EmailMessage()
    msg["Subject"] = f"Apex Lead Router: lead #{lead.id}"
    msg["From"] = SMTP_FROM
    msg["To"] = recipient
    msg.set_content(
        "\n".join(
            [
                f"Lead #{lead.id}",
                f"Name: {lead.full_name or '-'}",
                f"Phone: {lead.phone or '-'}",
                f"Email: {lead.email or '-'}",
                f"Facebook lead ID: {lead.fb_lead_id or '-'}",
            ]
        )
    )
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(msg)


async def send_lead_to_google_sheet(session: AsyncSession, lead: Lead, sheet_id: str | None) -> bool:
    if not sheet_id:
        return False
    if not GOOGLE_SHEETS_ENABLED:
        await create_delivery_log(
            session,
            lead_id=lead.id,
            channel=DeliveryChannel.google_sheet.value,
            recipient=sheet_id,
            status=DeliveryStatus.skipped.value,
            error_message="GOOGLE_SHEETS_ENABLED=false",
        )
        return False
    await create_delivery_log(
        session,
        lead_id=lead.id,
        channel=DeliveryChannel.google_sheet.value,
        recipient=sheet_id,
        status=DeliveryStatus.skipped.value,
        error_message="Google Sheets API client is not configured in this lightweight build.",
    )
    return False


async def deliver_lead(session: AsyncSession, lead_id: int, bot: Bot | None = None) -> Lead | None:
    lead = await get_lead_by_id(session, lead_id)
    if not lead:
        return None

    if not lead.form_id:
        await create_delivery_log(
            session,
            lead_id=lead.id,
            channel=DeliveryChannel.rule.value,
            recipient=None,
            status=DeliveryStatus.error.value,
            error_message="Lead has no mapped Facebook form.",
        )
        await mark_lead_delivery_state(session, lead, has_errors=True)
        return lead

    rule = await get_delivery_rule(session, SourceType.facebook_lead_form.value, lead.form_id)
    if not rule:
        await create_delivery_log(
            session,
            lead_id=lead.id,
            channel=DeliveryChannel.rule.value,
            recipient=str(lead.form_id),
            status=DeliveryStatus.error.value,
            error_message="No active delivery rule found.",
        )
        await mark_lead_delivery_state(session, lead, has_errors=True)
        return lead

    telegram_success = False
    email_success = False
    sheet_success = False
    has_errors = False

    if rule.send_to_admin:
        success, errors = await send_lead_to_admin(session, bot, lead)
        telegram_success = telegram_success or success
        has_errors = has_errors or errors

    for telegram_id in load_json_list(rule.telegram_ids_json):
        success = await send_lead_to_telegram(session, bot, lead, telegram_id)
        telegram_success = telegram_success or success

    for email in load_json_list(rule.emails_json):
        success = await send_lead_to_email(session, lead, str(email))
        email_success = email_success or success

    sheet_success = await send_lead_to_google_sheet(session, lead, rule.google_sheet_id)

    # Skipped channels are not treated as hard errors; missing rule and real send exceptions are.
    await mark_lead_delivery_state(
        session,
        lead,
        delivered_telegram=telegram_success,
        delivered_email=email_success,
        delivered_sheet=sheet_success,
        has_errors=has_errors,
    )
    return lead
