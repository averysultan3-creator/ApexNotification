from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preland_event import PrelandEvent, PrelandEventType
from app.services.preland_service import get_preland_by_slug
from app.utils.formatters import percent
from app.utils.security import hash_ip
from config import PUBLIC_BASE_URL


def _date_filter(stmt: Any, date_from: datetime | None, date_to: datetime | None) -> Any:
    if date_from is not None:
        stmt = stmt.where(PrelandEvent.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(PrelandEvent.created_at <= date_to)
    return stmt


async def track_page_view(
    session: AsyncSession,
    preland_slug: str,
    request_data: dict[str, Any],
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> PrelandEvent | None:
    preland = await get_preland_by_slug(session, preland_slug)
    if not preland:
        return None
    event = PrelandEvent(
        preland_id=preland.id,
        event_type=PrelandEventType.page_view.value,
        visitor_id=request_data.get("visitor_id"),
        ip_hash=hash_ip(ip),
        user_agent=user_agent,
        referer=request_data.get("referer"),
        utm_source=request_data.get("utm_source"),
        utm_campaign=request_data.get("utm_campaign"),
        utm_content=request_data.get("utm_content"),
        metadata_json=json.dumps({"url": request_data.get("url")}, ensure_ascii=False),
    )
    session.add(event)
    await session.flush()
    await session.refresh(event)
    return event


async def track_button_click(
    session: AsyncSession,
    preland_slug: str,
    button_id: str,
    request_data: dict[str, Any],
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> PrelandEvent | None:
    preland = await get_preland_by_slug(session, preland_slug)
    if not preland:
        return None
    event = PrelandEvent(
        preland_id=preland.id,
        event_type=PrelandEventType.button_click.value,
        button_id=button_id,
        visitor_id=request_data.get("visitor_id"),
        ip_hash=hash_ip(ip),
        user_agent=user_agent,
        referer=request_data.get("referer"),
        utm_source=request_data.get("utm_source"),
        utm_campaign=request_data.get("utm_campaign"),
        utm_content=request_data.get("utm_content"),
        metadata_json=json.dumps({"url": request_data.get("url")}, ensure_ascii=False),
    )
    session.add(event)
    await session.flush()
    await session.refresh(event)
    return event


async def get_preland_stats(
    session: AsyncSession,
    preland_id: int,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    visits_stmt = select(func.count()).select_from(PrelandEvent).where(
        PrelandEvent.preland_id == preland_id,
        PrelandEvent.event_type == PrelandEventType.page_view.value,
    )
    clicks_stmt = select(func.count()).select_from(PrelandEvent).where(
        PrelandEvent.preland_id == preland_id,
        PrelandEvent.event_type == PrelandEventType.button_click.value,
    )
    visits = int((await session.execute(_date_filter(visits_stmt, date_from, date_to))).scalar_one())
    clicks = int((await session.execute(_date_filter(clicks_stmt, date_from, date_to))).scalar_one())
    return {"visits": visits, "clicks": clicks, "ctr": percent(clicks, visits)}


async def get_preland_button_stats(
    session: AsyncSession,
    preland_id: int,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, int]:
    stmt = (
        select(PrelandEvent.button_id, func.count())
        .where(
            PrelandEvent.preland_id == preland_id,
            PrelandEvent.event_type == PrelandEventType.button_click.value,
            PrelandEvent.button_id.is_not(None),
        )
        .group_by(PrelandEvent.button_id)
        .order_by(func.count().desc())
    )
    rows = (await session.execute(_date_filter(stmt, date_from, date_to))).all()
    return {str(button_id): int(count) for button_id, count in rows}


def today_range() -> tuple[datetime, datetime]:
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def generate_tracking_code(preland_slug: str) -> str:
    return f'<script src="{PUBLIC_BASE_URL}/track/pixel.js?pl={preland_slug}"></script>'


def generate_tracking_script(preland_slug: str | None = None) -> str:
    base = PUBLIC_BASE_URL
    fallback = preland_slug or ""
    return f"""(function () {{
  var script = document.currentScript;
  var preland = script && script.getAttribute("src")
    ? new URL(script.getAttribute("src")).searchParams.get("pl")
    : "{fallback}";

  if (!preland) return;

  function visitorId() {{
    try {{
      var key = "apex_lr_vid";
      var existing = localStorage.getItem(key);
      if (existing) return existing;
      var value = (crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now()) + Math.random();
      localStorage.setItem(key, value);
      return value;
    }} catch (e) {{
      return null;
    }}
  }}

  function post(url, data) {{
    try {{
      data.visitor_id = visitorId();
      fetch(url, {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        keepalive: true,
        body: JSON.stringify(data)
      }}).catch(function () {{}});
    }} catch (e) {{}}
  }}

  var base = "{base}";
  var params = new URLSearchParams(window.location.search);

  post(base + "/track/page-view", {{
    preland_slug: preland,
    url: window.location.href,
    referer: document.referrer || null,
    utm_source: params.get("utm_source"),
    utm_campaign: params.get("utm_campaign"),
    utm_content: params.get("utm_content")
  }});

  document.addEventListener("click", function (e) {{
    var el = e.target.closest("[data-track-click]");
    if (!el) return;

    post(base + "/track/button-click", {{
      preland_slug: preland,
      button_id: el.getAttribute("data-track-click"),
      url: window.location.href,
      referer: document.referrer || null,
      utm_source: params.get("utm_source"),
      utm_campaign: params.get("utm_campaign"),
      utm_content: params.get("utm_content")
    }});
  }});
}})();
"""
