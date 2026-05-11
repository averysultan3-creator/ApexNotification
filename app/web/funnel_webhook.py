from __future__ import annotations
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.funnel_form_service import get_form_by_verify_token
from app.services.lead_service import create_lead, get_lead_by_fb_lead_id
from app.services.delivery_service import deliver_lead
from app.utils.facebook import LEADGEN_FIELD, graph_lead_url
from config import FACEBOOK_PAGE_ACCESS_TOKEN, FACEBOOK_GRAPH_VERSION
from database import get_session
import httpx

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/funnel", tags=["funnel"])


def _parse_events(payload: dict) -> list[dict]:
    events = []
    if not isinstance(payload, dict):
        return events
    for entry in payload.get("entry", []) or []:
        if not isinstance(entry, dict):
            continue
        page_id = str(entry.get("id") or "")
        for change in entry.get("changes", []) or []:
            if not isinstance(change, dict):
                continue
            if change.get("field") != LEADGEN_FIELD:
                continue
            val = change.get("value") or {}
            if not isinstance(val, dict):
                continue
            leadgen_id = val.get("leadgen_id") or val.get("lead_id")
            form_id = val.get("form_id")
            if leadgen_id and form_id:
                events.append({
                    "leadgen_id": str(leadgen_id),
                    "fb_form_id": str(form_id),
                    "fb_page_id": str(val.get("page_id") or page_id),
                })
    return events


async def _fetch_lead(leadgen_id: str) -> dict:
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        return {}
    try:
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
    except Exception as e:
        logger.error("fetch_lead %s: %s", leadgen_id, e)
        return {}


def _normalize(raw: dict) -> dict:
    fields: dict = {}
    for item in raw.get("field_data", []) or []:
        name = str(item.get("name") or "").strip()
        values = item.get("values") or []
        val = values[0] if isinstance(values, list) and values else values
        if name:
            fields[name] = val

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
        "utm_campaign", "utm_source", "utm_content", "utm_medium",
        "tag", "ref", "source", "campaign", "label",
    )
    return {
        "full_name": full_name,
        "phone": first("phone_number", "phone", "mobile"),
        "email": first("email", "email_address"),
        "telegram": first("telegram", "tg", "telegram_username", "username"),
        "tag": tag,
    }


@router.post("/{verify_token}/lead")
async def receive_lead(
    verify_token: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    form = await get_form_by_verify_token(session, verify_token)
    if not form:
        raise HTTPException(status_code=403, detail="Invalid verify token")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    events = _parse_events(payload)
    processed = 0
    for event in events:
        try:
            if await get_lead_by_fb_lead_id(session, event["leadgen_id"]):
                continue
            raw = await _fetch_lead(event["leadgen_id"])
            norm = _normalize(raw)
            tag = norm.get("tag") or form.tag
            lead = await create_lead(
                session,
                funnel_form_id=form.id,
                fb_lead_id=event["leadgen_id"],
                fb_form_id=event["fb_form_id"],
                fb_page_id=event["fb_page_id"],
                full_name=norm.get("full_name"),
                phone=norm.get("phone"),
                email=norm.get("email"),
                telegram=norm.get("telegram"),
                tag=tag,
                raw_data_json=json.dumps(raw, ensure_ascii=False),
            )
            bot = getattr(request.app.state, "bot", None)
            await deliver_lead(session, bot, lead)
            processed += 1
        except Exception as e:
            logger.error("process event %s: %s", event, e)

    return {"ok": True, "processed": processed}
