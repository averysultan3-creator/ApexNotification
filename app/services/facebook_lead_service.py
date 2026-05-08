from __future__ import annotations
import json
import logging
from typing import Any
import httpx
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.delivery_service import deliver_lead
from app.services.facebook_form_service import get_form_by_fb_form_id
from app.services.lead_service import create_lead, get_lead_by_fb_lead_id
from app.utils.facebook import LEADGEN_FIELD, graph_lead_url
from config import FACEBOOK_GRAPH_VERSION, FACEBOOK_PAGE_ACCESS_TOKEN, FACEBOOK_VERIFY_TOKEN

logger = logging.getLogger(__name__)


def verify_facebook_webhook(
    mode: str | None, verify_token: str | None, challenge: str | None
) -> str | None:
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
                events.append({
                    "leadgen_id": str(leadgen_id),
                    "form_id": str(form_id),
                    "page_id": str(page_id),
                })
    return events


async def fetch_lead_details(leadgen_id: str) -> dict[str, Any]:
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        raise RuntimeError("FACEBOOK_PAGE_ACCESS_TOKEN is not configured.")
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            graph_lead_url(FACEBOOK_GRAPH_VERSION, leadgen_id),
            params={
                "fields": "field_data,created_time,form_id",
                "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
            },
        )
        r.raise_for_status()
        return r.json()


def normalize_lead_data(raw: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for item in raw.get("field_data", []) or []:
        name = str(item.get("name") or "").strip()
        values = item.get("values") or []
        value = values[0] if isinstance(values, list) and values else values
        if name:
            fields[name] = value

    def first(*names: str) -> str | None:
        for n in names:
            v = fields.get(n)
            if v:
                return str(v)
        return None

    full_name = first("full_name", "name", "your_name") or (
        " ".join(p for p in [first("first_name"), first("last_name")] if p) or None
    )
    tag = first(
        "utm_campaign", "utm_source", "utm_content", "utm_medium", "utm_term",
        "tag", "ref", "source", "campaign", "label",
    )
    return {
        "full_name": full_name,
        "phone": first("phone_number", "phone", "телефон", "mobile"),
        "email": first("email", "email_address", "почта"),
        "tag": tag,
    }


async def process_facebook_lead(
    session: AsyncSession, payload: dict[str, Any], *, bot: Bot | None = None
) -> list[Any]:
    events = parse_facebook_webhook_payload(payload)
    leads = []
    for event in events:
        try:
            lead = await _process_one(session, event, bot=bot)
            if lead:
                leads.append(lead)
        except Exception as e:
            logger.error("Error processing lead %s: %s", event, e)
    return leads


async def _process_one(session: AsyncSession, event: dict[str, str], *, bot: Bot | None = None):
    leadgen_id = event["leadgen_id"]
    fb_form_id = event["form_id"]

    if await get_lead_by_fb_lead_id(session, leadgen_id):
        return None

    form = await get_form_by_fb_form_id(session, fb_form_id)

    try:
        raw = await fetch_lead_details(leadgen_id)
    except Exception as e:
        logger.error("Fetch lead %s failed: %s", leadgen_id, e)
        raw = {}

    norm = normalize_lead_data(raw)
    # tag fallback: utm-поле → offer_name формы → имя формы
    tag = norm.get("tag") or (form.offer_name if form and form.offer_name else None) or (form.name if form else None)
    lead = await create_lead(
        session,
        client_id=form.client_id if form else None,
        facebook_form_id=form.id if form else None,
        fb_lead_id=leadgen_id,
        full_name=norm.get("full_name"),
        phone=norm.get("phone"),
        email=norm.get("email"),
        tag=tag,
        raw_data_json=json.dumps(raw, ensure_ascii=False),
    )
    await deliver_lead(session, bot, lead)
    return lead
