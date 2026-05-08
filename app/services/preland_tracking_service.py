from __future__ import annotations
from datetime import datetime
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.preland_event import PrelandEvent, PrelandEventType
from app.services.preland_service import get_preland_by_slug
from config import PUBLIC_BASE_URL


def generate_tracking_script(slug: str | None, base_url: str = "") -> str:
    if not slug:
        return "// No preland slug provided"
    url = (base_url or PUBLIC_BASE_URL).rstrip("/")
    return (
        "(function(){{"
        "var APEX=\"{url}\",PL=\"{slug}\";"
        "function uid(){{return Math.random().toString(36).slice(2)+(+new Date).toString(36);}}"
        "var vid=localStorage.getItem(\"_apx_vid\");if(!vid){{vid=uid();localStorage.setItem(\"_apx_vid\",vid);}}"
        "function send(ep,data){{"
        "var body=JSON.stringify(Object.assign({{preland_slug:PL,visitor_id:vid}},data));"
        "if(navigator.sendBeacon){{navigator.sendBeacon(APEX+ep,body);}}"
        "else{{var x=new XMLHttpRequest();x.open(\"POST\",APEX+ep);"
        "x.setRequestHeader(\"Content-Type\",\"application/json\");x.send(body);}}}}"
        "var p=new URLSearchParams(location.search);"
        "send(\"/track/page-view\",{{url:location.href,referer:document.referrer,"
        "utm_source:p.get(\"utm_source\"),utm_campaign:p.get(\"utm_campaign\")}});"
        "document.querySelectorAll(\"[data-track-click]\").forEach(function(el){{"
        "el.addEventListener(\"click\",function(){{"
        "send(\"/track/button-click\",{{button_id:el.getAttribute(\"data-track-click\"),url:location.href}});}});}});"
        "}})()"
    ).format(url=url, slug=slug)


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
        utm_source=request_data.get("utm_source"),
        utm_campaign=request_data.get("utm_campaign"),
    )
    session.add(event)
    await session.flush()
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
        utm_source=request_data.get("utm_source"),
        utm_campaign=request_data.get("utm_campaign"),
    )
    session.add(event)
    await session.flush()
    return event


async def get_preland_stats(
    session: AsyncSession,
    preland_id: int,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    def _base(event_type: str):
        stmt = select(func.count()).select_from(PrelandEvent).where(
            PrelandEvent.preland_id == preland_id,
            PrelandEvent.event_type == event_type,
        )
        if date_from:
            stmt = stmt.where(PrelandEvent.created_at >= date_from)
        if date_to:
            stmt = stmt.where(PrelandEvent.created_at <= date_to)
        return stmt

    visits = (await session.execute(_base(PrelandEventType.page_view.value))).scalar() or 0
    clicks = (await session.execute(_base(PrelandEventType.button_click.value))).scalar() or 0
    ctr = round(clicks / visits * 100, 1) if visits else 0.0
    return {"visits": visits, "clicks": clicks, "ctr": ctr}


async def get_preland_button_stats(session: AsyncSession, preland_id: int) -> dict[str, int]:
    rows = (await session.execute(
        select(PrelandEvent.button_id, func.count().label("cnt"))
        .where(
            PrelandEvent.preland_id == preland_id,
            PrelandEvent.event_type == PrelandEventType.button_click.value,
            PrelandEvent.button_id.isnot(None),
        )
        .group_by(PrelandEvent.button_id)
        .order_by(func.count().desc())
    )).all()
    return {row.button_id: row.cnt for row in rows}
