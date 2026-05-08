from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.preland_tracking_service import (
    generate_tracking_script,
    track_button_click,
    track_page_view,
)
from database import get_session

router = APIRouter(prefix="/track", tags=["preland-tracking"])


@router.get("/pixel.js")
async def pixel_js(pl: str | None = Query(default=None)) -> Response:
    return Response(
        content=generate_tracking_script(pl),
        media_type="application/javascript; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/page-view")
async def page_view(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool | str]:
    data = await request.json()
    slug = data.get("preland_slug")
    if not slug:
        return {"ok": False, "error": "preland_slug_required"}
    event = await track_page_view(
        session,
        slug,
        data,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"ok": bool(event)}


@router.post("/button-click")
async def button_click(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool | str]:
    data = await request.json()
    slug = data.get("preland_slug")
    button_id = data.get("button_id")
    if not slug:
        return {"ok": False, "error": "preland_slug_required"}
    if not button_id:
        return {"ok": False, "error": "button_id_required"}
    event = await track_button_click(
        session,
        slug,
        str(button_id),
        data,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"ok": bool(event)}
