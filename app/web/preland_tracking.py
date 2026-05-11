import json as _json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.preland_tracking_service import (
    generate_tracking_script,
    track_button_click,
    track_page_view,
)
from database import get_session


async def _parse_body(request: Request) -> dict:
    """Parse JSON body regardless of Content-Type (sendBeacon sends text/plain)."""
    try:
        return await request.json()
    except Exception:
        pass
    try:
        raw = await request.body()
        return _json.loads(raw)
    except Exception:
        return {}

# 1x1 transparent GIF
_GIF = bytes([
    0x47,0x49,0x46,0x38,0x39,0x61,0x01,0x00,0x01,0x00,
    0x80,0x00,0x00,0xFF,0xFF,0xFF,0x00,0x00,0x00,0x21,
    0xF9,0x04,0x00,0x00,0x00,0x00,0x00,0x2C,0x00,0x00,
    0x00,0x00,0x01,0x00,0x01,0x00,0x00,0x02,0x02,0x44,
    0x01,0x00,0x3B,
])
_GIF_HEADERS = {"Cache-Control": "no-store, no-cache", "Access-Control-Allow-Origin": "*"}

router = APIRouter(prefix="/track", tags=["preland-tracking"])


@router.get("/pixel.js")
async def pixel_js(pl: str | None = Query(default=None)) -> Response:
    return Response(
        content=generate_tracking_script(pl),
        media_type="application/javascript; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


@router.api_route("/pv", methods=["GET", "POST"])
async def pv_pixel(
    request: Request,
    pl: str | None = Query(default=None),
    vid: str | None = Query(default=None),
    utm_source: str | None = Query(default=None),
    utm_campaign: str | None = Query(default=None),
    url: str | None = Query(default=None),
    ref: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> Response:
    if pl:
        await track_page_view(
            session, pl,
            {"visitor_id": vid, "utm_source": utm_source, "utm_campaign": utm_campaign,
             "url": url, "referrer": ref},
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    return Response(content=_GIF, media_type="image/gif", headers=_GIF_HEADERS)


@router.api_route("/bc", methods=["GET", "POST"])
async def bc_pixel(
    request: Request,
    pl: str | None = Query(default=None),
    vid: str | None = Query(default=None),
    b: str | None = Query(default=None),
    utm_source: str | None = Query(default=None),
    utm_campaign: str | None = Query(default=None),
    url: str | None = Query(default=None),
    ref: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> Response:
    if pl and b:
        await track_button_click(
            session, pl, b,
            {"visitor_id": vid, "utm_source": utm_source, "utm_campaign": utm_campaign,
             "url": url, "referrer": ref},
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    return Response(content=_GIF, media_type="image/gif", headers=_GIF_HEADERS)


@router.post("/page-view")
async def page_view(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool | str]:
    data = await _parse_body(request)
    slug = data.get("preland_slug")
    if not slug:
        return {"ok": False, "error": "preland_slug_required"}
    try:
        event = await track_page_view(
            session,
            slug,
            data,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception:
        return {"ok": False, "error": "tracking_failed"}
    return {"ok": bool(event)}


@router.post("/button-click")
async def button_click(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool | str]:
    data = await _parse_body(request)
    slug = data.get("preland_slug")
    button_id = data.get("button_id")
    if not slug:
        return {"ok": False, "error": "preland_slug_required"}
    if not button_id:
        return {"ok": False, "error": "button_id_required"}
    try:
        event = await track_button_click(
            session,
            slug,
            str(button_id),
            data,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception:
        return {"ok": False, "error": "tracking_failed"}
    return {"ok": bool(event)}
