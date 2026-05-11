from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from database import AsyncSessionLocal

router = APIRouter()


@router.get("/health")
async def health() -> JSONResponse:
    db_status = "ok"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    ok = db_status == "ok"
    result = {
        "status": "ok" if ok else "error",
        "service": "apex-lead-router",
        "db": db_status,
        "time": datetime.utcnow().isoformat(),
    }
    return JSONResponse(content=result, status_code=200 if ok else 503)
