from __future__ import annotations
import json
from datetime import datetime
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.preland_event import PrelandEvent, PrelandEventType
from app.services.preland_link_service import get_link_by_slug
from config import PUBLIC_BASE_URL


def generate_tracking_script(
    slug: str | None = None,
    base_url: str = "",
    track_clicks: bool = True,
) -> str:
    """
    Returns a self-contained JS snippet.

    Priority for PL slug:
      1. ?pl= query param from the ad URL  (highest — set by our tracking link)
      2. default slug baked into the script (set when generating per-link code)
      3. ?pl= in the script src attribute
      4. auto-slug from hostname+path       (lowest — fallback for site-level script)

    Sending strategy (most → least reliable):
      - sendBeacon  — fire-and-forget, browser guarantees delivery even on navigation
      - Image pixel — instant, no CORS, fallback when sendBeacon absent

    track_clicks: if False — only page_view is sent, no click listener added.
    """
    url = (base_url or PUBLIC_BASE_URL).rstrip("/")
    pl_js = json.dumps(slug) if slug else "null"
    return (
        "(function(){try{"
        f"var APEX={json.dumps(url)},_DEF_PL={pl_js};"
        # 1. ?pl= from ad URL — ALWAYS highest priority
        "var _p=new URLSearchParams(location.search);"
        "var PL=_p.get('pl')||null;"
        # 2. default slug baked in
        "if(!PL)PL=_DEF_PL;"
        # 3. ?pl= from script src
        "if(!PL){var _sc=document.currentScript;if(_sc){var _su=_sc.getAttribute('src')||'';"
        "var _pm=_su.match(/[?&]pl=([^&]+)/);if(_pm)PL=decodeURIComponent(_pm[1]);}}"
        # 4. auto-slug
        "if(!PL){var _h=(location.hostname||'').replace(/^www\\./,''),"
        "_pa=(location.pathname||'/').replace(/\\/+$/,'')||'/';"
        "PL=(_h+_pa).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'').slice(0,80)||'auto';}"
        # persistent visitor id
        "var _vid=null;"
        "try{_vid=localStorage.getItem('_apx_vid');"
        "if(!_vid){_vid=Math.random().toString(36).slice(2)+(+new Date).toString(36);"
        "localStorage.setItem('_apx_vid',_vid);}}catch(_e){"
        "_vid=Math.random().toString(36).slice(2)+(+new Date).toString(36);}"
        # query builder
        "function _qs(ex){var q={pl:PL,vid:_vid,"
        "utm_source:_p.get('utm_source')||'',"
        "utm_campaign:_p.get('utm_campaign')||'',"
        "ref:encodeURIComponent(document.referrer||'')};"
        "if(ex)for(var k in ex)q[k]=ex[k];"
        "return Object.keys(q).map(function(k){"
        "return encodeURIComponent(k)+'='+encodeURIComponent(q[k]||'');}).join('&');}"
        # send: sendBeacon (guaranteed on navigation) → Image pixel fallback
        "function _send(ep,ex){var u=APEX+ep+'?'+_qs(ex);"
        "if(navigator.sendBeacon){try{navigator.sendBeacon(u);return;}catch(_e){}}"
        "try{new Image().src=u;}catch(_e){}}"
        # page view
        "_send('/track/pv');"
        +
        # click tracking — optional, sendBeacon works even when browser navigates away
        (
        "document.addEventListener('click',function(ev){"
        "var el=ev.target;"
        "while(el&&el!==document){"
        "if(el.getAttribute){"
        # data-track-click attribute — explicit button tracking
        "var _t=el.getAttribute('data-track-click');"
        "if(_t){_send('/track/bc',{b:_t});return;}"
        # auto-detect Telegram / WhatsApp CTA links
        "if(el.tagName==='A'){"
        "var _hr=(el.getAttribute('href')||'').toLowerCase();"
        "if(_hr.indexOf('t.me/')>-1||_hr.indexOf('tg://')===0"
        "||_hr.indexOf('telegram.me/')>-1"
        "||_hr.indexOf('wa.me/')>-1"
        "||_hr.indexOf('whatsapp.com')>-1){"
        "_send('/track/bc',{b:'cta'});return;}}}"
        "el=el.parentNode;}},true);"
        if track_clicks else ""
        )
        + "}catch(_e){}})();"
    )


async def _resolve_link_id(session: AsyncSession, slug: str) -> int | None:
    link = await get_link_by_slug(session, slug)
    return link.id if link else None


async def track_page_view(
    session: AsyncSession,
    preland_slug: str,
    request_data: dict[str, Any],
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> PrelandEvent | None:
    slug = preland_slug
    link_id = await _resolve_link_id(session, slug)
    visitor_id = (request_data.get("visitor_id") or "").strip() or None

    if visitor_id and link_id:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        existing = (await session.execute(
            select(PrelandEvent.id).where(
                PrelandEvent.link_id == link_id,
                PrelandEvent.event_type == PrelandEventType.page_view.value,
                PrelandEvent.visitor_id == visitor_id,
                PrelandEvent.created_at >= today_start,
            ).limit(1)
        )).first()
        if existing:
            return None

    event = PrelandEvent(
        link_id=link_id,
        slug=slug,
        event_type=PrelandEventType.page_view.value,
        visitor_id=visitor_id,
        utm_source=request_data.get("utm_source"),
        utm_campaign=request_data.get("utm_campaign"),
        referrer=(request_data.get("referrer") or "")[:500] or None,
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
    slug = preland_slug
    link_id = await _resolve_link_id(session, slug)
    visitor_id = (request_data.get("visitor_id") or "").strip() or None

    if visitor_id and link_id:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        existing = (await session.execute(
            select(PrelandEvent.id).where(
                PrelandEvent.link_id == link_id,
                PrelandEvent.event_type == PrelandEventType.button_click.value,
                PrelandEvent.button_id == str(button_id),
                PrelandEvent.visitor_id == visitor_id,
                PrelandEvent.created_at >= today_start,
            ).limit(1)
        )).first()
        if existing:
            return None

    event = PrelandEvent(
        link_id=link_id,
        slug=slug,
        event_type=PrelandEventType.button_click.value,
        button_id=button_id,
        visitor_id=visitor_id,
        utm_source=request_data.get("utm_source"),
        utm_campaign=request_data.get("utm_campaign"),
        referrer=(request_data.get("referrer") or "")[:500] or None,
    )
    session.add(event)
    await session.flush()
    return event


async def get_link_stats(
    session: AsyncSession,
    link_id: int,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    def _base(event_type: str):
        stmt = select(func.count()).select_from(PrelandEvent).where(
            PrelandEvent.link_id == link_id,
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


# Keep old name as alias for any existing callers
async def get_preland_stats(
    session: AsyncSession,
    preland_id: int,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    return await get_link_stats(session, preland_id, date_from, date_to)


async def get_link_hourly_stats(
    session: AsyncSession, link_id: int, date_from: datetime
) -> list[dict[str, Any]]:
    from sqlalchemy import extract
    rows_v = (await session.execute(
        select(
            extract("hour", PrelandEvent.created_at).label("hour"),
            func.count().label("cnt"),
        )
        .where(
            PrelandEvent.link_id == link_id,
            PrelandEvent.event_type == PrelandEventType.page_view.value,
            PrelandEvent.created_at >= date_from,
        )
        .group_by("hour")
        .order_by("hour")
    )).all()
    rows_c = (await session.execute(
        select(
            extract("hour", PrelandEvent.created_at).label("hour"),
            func.count().label("cnt"),
        )
        .where(
            PrelandEvent.link_id == link_id,
            PrelandEvent.event_type == PrelandEventType.button_click.value,
            PrelandEvent.created_at >= date_from,
        )
        .group_by("hour")
        .order_by("hour")
    )).all()
    views_by_h = {int(r.hour): r.cnt for r in rows_v}
    clicks_by_h = {int(r.hour): r.cnt for r in rows_c}
    all_hours = sorted(set(views_by_h) | set(clicks_by_h))
    return [
        {"hour": h, "views": views_by_h.get(h, 0), "clicks": clicks_by_h.get(h, 0),
         "ctr": round(clicks_by_h.get(h, 0) / views_by_h[h] * 100, 1) if views_by_h.get(h) else 0.0}
        for h in all_hours
    ]


async def get_site_stats(
    session: AsyncSession,
    site_id: int,
    date_from: datetime | None = None,
) -> dict[str, Any]:
    import re
    from urllib.parse import urlparse
    from sqlalchemy import or_
    from app.models.preland_link import PrelandLink
    from app.models.preland_site import PrelandSite

    # Compute auto-slug the same way JS does (from site base_url)
    site_row = (await session.execute(
        select(PrelandSite.base_url, PrelandSite.name).where(PrelandSite.id == site_id)
    )).first()
    auto_slugs: list[str] = []
    if site_row:
        parsed = urlparse((site_row.base_url or "").rstrip("/"))
        h = (parsed.hostname or "")
        if h.startswith("www."):
            h = h[4:]
        pa = parsed.path.rstrip("/") or "/"
        auto_slug = re.sub(r"[^a-z0-9]+", "-", (h + pa).lower()).strip("-")[:80] or "auto"
        auto_slugs.append(auto_slug)
        # Also include site.name as slug (e.g. "pl-skyx-girl" from <script src="...?pl=pl-skyx-girl">)
        if site_row.name:
            auto_slugs.append(site_row.name)

    # All link IDs for this site
    link_ids = list((await session.execute(
        select(PrelandLink.id).where(PrelandLink.site_id == site_id)
    )).scalars().all())

    # Match events by link_id OR by direct slug
    conditions = []
    if link_ids:
        conditions.append(PrelandEvent.link_id.in_(link_ids))
    for s in auto_slugs:
        conditions.append(PrelandEvent.slug == s)

    if not conditions:
        return {"visits": 0, "clicks": 0, "ctr": 0.0}

    def _base(event_type: str):
        stmt = (
            select(func.count())
            .select_from(PrelandEvent)
            .where(PrelandEvent.event_type == event_type, or_(*conditions))
        )
        if date_from:
            stmt = stmt.where(PrelandEvent.created_at >= date_from)
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


async def get_link_button_stats(session: AsyncSession, link_id: int) -> dict[str, int]:
    """Button click breakdown for a PrelandLink (new system)."""
    rows = (await session.execute(
        select(PrelandEvent.button_id, func.count().label("cnt"))
        .where(
            PrelandEvent.link_id == link_id,
            PrelandEvent.event_type == PrelandEventType.button_click.value,
            PrelandEvent.button_id.isnot(None),
        )
        .group_by(PrelandEvent.button_id)
        .order_by(func.count().desc())
    )).all()
    return {row.button_id: row.cnt for row in rows}


async def get_link_recent_events(
    session: AsyncSession, link_id: int, limit: int = 10
) -> list[dict]:
    """Last N events for a link — used by the bot's 'Проверить трекинг' button."""
    rows = (await session.execute(
        select(PrelandEvent)
        .where(PrelandEvent.link_id == link_id)
        .order_by(PrelandEvent.created_at.desc())
        .limit(limit)
    )).scalars().all()
    result = []
    for ev in rows:
        result.append({
            "type": ev.event_type,
            "button_id": ev.button_id,
            "visitor_id": (ev.visitor_id or "")[:8],
            "created_at": ev.created_at,
        })
    return result


async def get_site_recent_events(
    session: AsyncSession, site_id: int, limit: int = 10
) -> list[dict]:
    """Last N events across all links of a site."""
    from app.models.preland_link import PrelandLink
    rows = (await session.execute(
        select(PrelandEvent)
        .join(PrelandLink, PrelandEvent.link_id == PrelandLink.id)
        .where(PrelandLink.site_id == site_id)
        .order_by(PrelandEvent.created_at.desc())
        .limit(limit)
    )).scalars().all()
    result = []
    for ev in rows:
        result.append({
            "type": ev.event_type,
            "button_id": ev.button_id,
            "slug": ev.slug or "",
            "visitor_id": (ev.visitor_id or "")[:8],
            "created_at": ev.created_at,
        })
    return result


async def check_test_slug_received(
    session: AsyncSession, test_slug: str, since_seconds: int = 300
) -> bool:
    """Return True if at least one event with this slug arrived in the last N seconds."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(seconds=since_seconds)
    row = (await session.execute(
        select(PrelandEvent.id)
        .where(
            PrelandEvent.slug == test_slug,
            PrelandEvent.created_at >= cutoff,
        )
        .limit(1)
    )).first()
    return row is not None


async def check_site_event_since(
    session: AsyncSession,
    site_id: int,
    site_base_url: str,
    since: float,
) -> bool:
    """Return True if any tracking event for this site arrived since `since` (unix timestamp).

    Looks for events either:
    - linked to a PrelandLink that belongs to the site (link_id)
    - stored with the auto-generated slug that JS computes from hostname+pathname
    """
    import re
    from urllib.parse import urlparse
    from sqlalchemy import or_
    from app.models.preland_link import PrelandLink

    since_dt = datetime.utcfromtimestamp(since)

    # Compute the slug JS auto-generates from the site URL (when no ?pl= in script src)
    parsed = urlparse((site_base_url or "").rstrip("/"))
    h = (parsed.hostname or "")
    if h.startswith("www."):
        h = h[4:]
    pa = parsed.path.rstrip("/") or "/"
    auto_slug = re.sub(r"[^a-z0-9]+", "-", (h + pa).lower()).strip("-")[:80] or "auto"

    # Get all PrelandLink IDs for this site
    link_ids = list((await session.execute(
        select(PrelandLink.id).where(PrelandLink.site_id == site_id)
    )).scalars().all())

    conditions = [PrelandEvent.slug == auto_slug]
    if link_ids:
        conditions.append(PrelandEvent.link_id.in_(link_ids))

    row = (await session.execute(
        select(PrelandEvent.id)
        .where(PrelandEvent.created_at >= since_dt, or_(*conditions))
        .limit(1)
    )).first()
    return row is not None

