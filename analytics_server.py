"""
analytics_server.py — Lightweight HTTP server for prelanding analytics.

Receives events from static prelanding pages (GitHub Pages, etc.)
and stores them in the shared SQLite database.

Usage:
    python analytics_server.py [--port 8080] [--host 0.0.0.0]

Environment variables:
    ANALYTICS_PORT     default 8080
    ANALYTICS_HOST     default 0.0.0.0
    ANALYTICS_TOKEN    optional bearer token for extra security
    BOT_TOKEN          required (for config/db import)
    ADMIN_IDS          required (for config/db import)

The server emits CORS headers so GitHub Pages (or any other static host)
can POST to it directly from the browser.
"""
import asyncio
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone

# ── ensure project root is on sys.path ───────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiohttp import web
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("analytics_server")

# ── DB setup ──────────────────────────────────────────────────────────────────
from config import DATABASE_URL  # noqa: E402  (import after sys.path)
import models  # noqa: F401  register all ORM classes

from database import Base
from models.site_event import SiteEvent

_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)
_SessionFactory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

# ── Optional bearer token auth ────────────────────────────────────────────────
_ANALYTICS_TOKEN: str = os.getenv("ANALYTICS_TOKEN", "")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _ua_hash(ua: str) -> str:
    """Return first 8 hex chars of SHA-1(user-agent) — no PII stored."""
    return hashlib.sha1(ua.encode("utf-8", errors="replace")).hexdigest()[:8]


# ── CORS helper ───────────────────────────────────────────────────────────────
_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "86400",
}


async def _cors_preflight(request: web.Request) -> web.Response:
    return web.Response(headers=_CORS_HEADERS)


async def _check_auth(request: web.Request) -> bool:
    if not _ANALYTICS_TOKEN:
        return True
    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {_ANALYTICS_TOKEN}"


# ── POST /event ────────────────────────────────────────────────────────────────
async def handle_event(request: web.Request) -> web.Response:
    """
    Receive a tracking event from the prelanding page.

    Expected JSON body:
        {
            "type":       "visit" | "cta_click" | "leave",
            "session_id": "<uuid>",
            "site_id":    "skyx_pl_1830",       // optional
            "ref_code":   "abc123",             // optional, from URL ?ref=
            "time_spent": 42                    // optional, seconds (for leave)
        }
    """
    if not await _check_auth(request):
        return web.json_response({"error": "unauthorized"}, status=401, headers=_CORS_HEADERS)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400, headers=_CORS_HEADERS)

    event_type = str(body.get("type", "")).strip()
    session_id = str(body.get("session_id", "")).strip()

    if event_type not in ("visit", "cta_click", "leave"):
        return web.json_response({"error": "unknown type"}, status=400, headers=_CORS_HEADERS)
    if not session_id or len(session_id) > 36:
        return web.json_response({"error": "bad session_id"}, status=400, headers=_CORS_HEADERS)

    site_id = str(body.get("site_id", "") or "")[:100]
    ref_code = str(body.get("ref_code", "") or "")[:100]
    time_spent_raw = body.get("time_spent")
    time_spent = int(time_spent_raw) if isinstance(time_spent_raw, (int, float)) and time_spent_raw >= 0 else None
    ua = request.headers.get("User-Agent", "")
    ua_hash_val = _ua_hash(ua) if ua else None

    event = SiteEvent(
        event_type=event_type,
        session_id=session_id,
        site_id=site_id or None,
        ref_code=ref_code or None,
        time_spent=time_spent,
        ua_hash=ua_hash_val,
        date=_today(),
        created_at=_now_utc(),
    )

    async with _SessionFactory() as db:
        db.add(event)
        await db.commit()

    logger.info("event=%s site=%s sid=%.8s time=%s", event_type, site_id, session_id, time_spent)
    return web.json_response({"ok": True}, headers=_CORS_HEADERS)


# ── GET /ping ─────────────────────────────────────────────────────────────────
async def handle_ping(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "ts": _today()})


# ── App factory ───────────────────────────────────────────────────────────────
def make_app() -> web.Application:
    app = web.Application()

    # Ensure tables exist (idempotent)
    async def _on_startup(app):
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("DB tables verified / created.")

    app.on_startup.append(_on_startup)

    app.router.add_route("OPTIONS", "/event", _cors_preflight)
    app.router.add_post("/event", handle_event)
    app.router.add_get("/ping", handle_ping)
    return app


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ApexNotification analytics server")
    parser.add_argument("--host", default=os.getenv("ANALYTICS_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("ANALYTICS_PORT", "8080")))
    args = parser.parse_args()

    logger.info("Starting analytics server on %s:%s", args.host, args.port)
    web.run_app(make_app(), host=args.host, port=args.port)
