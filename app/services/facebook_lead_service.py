from __future__ import annotations

from typing import Any

import httpx
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import SourceType
from app.services.delivery_service import deliver_lead
from app.services.facebook_form_service import get_facebook_form_by_fb_form_id
from app.services.lead_service import create_lead, get_lead_by_fb_lead_id
from app.utils.facebook import LEADGEN_FIELD, graph_lead_url
from config import FACEBOOK_GRAPH_VERSION, FACEBOOK_PAGE_ACCESS_TOKEN, FACEBOOK_VERIFY_TOKEN


def verify_facebook_webhook(mode: str | None, verify_token: str | None, challenge: str | None) -> str | None:
    if mode == "subscribe" and verify_token == FACEBOOK_VERIFY_TOKEN and challenge is not None:
        return challenge
    return None


def parse_facebook_webhook_payload(payload: dict[str, Any]) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    for entry in payload.get("entry", []) or []:
        entry_page_id = str(entry.get("id") or "")
        for change in entry.get("changes", []) or []:
            if change.get("field") != LEADGEN_FIELD:
                continue
            value = change.get("value") or {}
            leadgen_id = value.get("leadgen_id") or value.get("lead_id")
            form_id = value.get("form_id")
            page_id = value.get("page_id") or entry_page_id
            if leadgen_id and form_id:
                events.append(
                    {
                        "leadgen_id": str(leadgen_id),
                        "form_id": str(form_id),
                        "page_id": str(page_id),
                    }
                )
    return events


async def fetch_lead_details(leadgen_id: str) -> dict[str, Any]:
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        raise RuntimeError("FACEBOOK_PAGE_ACCESS_TOKEN is not configured.")
    params = {
        "fields": "field_data,created_time,ad_id,form_id",
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(graph_lead_url(FACEBOOK_GRAPH_VERSION, leadgen_id), params=params)
        response.raise_for_status()
        return response.json()


def normalize_lead_data(raw: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for item in raw.get("field_data", []) or []:
        name = str(item.get("name") or "").strip()
        values = item.get("values") or []
        value = values[0] if isinstance(values, list) and values else values
        if name:
            fields[name] = value

    def first(*names: str) -> str | None:
        for name in names:
            value = fields.get(name)
            if value:
                return str(value)
        return None

    full_name = first("full_name", "name", "first_name", "your_name", "имя")
    if not full_name:
        first_name = first("first_name")
        last_name = first("last_name")
        full_name = " ".join(part for part in [first_name, last_name] if part) or None

    return {
        "full_name": full_name,
        "phone": first("phone_number", "phone", "mobile", "номер_телефона", "телефон"),
        "email": first("email", "e-mail"),
        "telegram": first("telegram", "telegram_username", "tg"),
        "fields": fields,
    }


async def create_lead_from_facebook(
    session: AsyncSession,
    event: dict[str, str],
    *,
    raw_details: dict[str, Any] | None = None,
) -> Any | None:
    existing = await get_lead_by_fb_lead_id(session, event["leadgen_id"])
    if existing:
        return existing

    form = await get_facebook_form_by_fb_form_id(session, event["form_id"])
    if not form:
        return None

    raw = raw_details if raw_details is not None else await fetch_lead_details(event["leadgen_id"])
    normalized = normalize_lead_data(raw)
    return await create_lead(
        session,
        source_type=SourceType.facebook_lead_form.value,
        fb_lead_id=event["leadgen_id"],
        fb_page_id=event.get("page_id"),
        fb_form_id=event.get("form_id"),
        client_id=form.client_id,
        form_id=form.id,
        raw_data=raw,
        normalized_data=normalized,
        full_name=normalized.get("full_name"),
        phone=normalized.get("phone"),
        email=normalized.get("email"),
        telegram=normalized.get("telegram"),
    )


async def process_facebook_lead(
    session: AsyncSession,
    payload: dict[str, Any],
    *,
    bot: Bot | None = None,
) -> list[Any]:
    processed = []
    for event in parse_facebook_webhook_payload(payload):
        lead = await create_lead_from_facebook(session, event)
        if lead:
            await deliver_lead(session, lead.id, bot=bot)
            processed.append(lead)
    return processed
