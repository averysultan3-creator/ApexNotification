from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.facebook_lead_service import process_facebook_lead, verify_facebook_webhook
from app.utils.security import verify_facebook_signature
from config import FACEBOOK_APP_SECRET
from database import get_session

router = APIRouter(prefix="/webhooks/facebook", tags=["facebook"])


@router.get("")
async def verify(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    challenge = verify_facebook_webhook(hub_mode, hub_verify_token, hub_challenge)
    if challenge is None:
        raise HTTPException(status_code=403, detail="Invalid verify token")
    return PlainTextResponse(challenge)


@router.post("")
async def receive(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, int | str]:
    body = await request.body()
    if not verify_facebook_signature(FACEBOOK_APP_SECRET, body, request.headers.get("x-hub-signature-256")):
        raise HTTPException(status_code=403, detail="Invalid Facebook signature")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")
    bot = getattr(request.app.state, "bot", None)
    leads = await process_facebook_lead(session, payload, bot=bot)
    return {"status": "ok", "processed": len(leads)}
