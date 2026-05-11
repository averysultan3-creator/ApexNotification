from __future__ import annotations
import logging
from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session
from fastapi import Depends
from app.services.google_sheet_service import handle_google_sheet_lead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/google-sheet", tags=["google-sheet"])


@router.post("/lead")
async def receive_lead(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        payload = await request.json()
    except Exception:
        return {"ok": False, "error": "invalid_json"}

    logger.info("google_sheet payload: %s", payload)
    bot = getattr(request.app.state, "bot", None)
    return await handle_google_sheet_lead(session, bot, payload)
