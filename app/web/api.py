from aiogram import Bot
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.web.facebook_webhook import router as facebook_router
from app.web.funnel_webhook import router as funnel_router
from app.web.google_sheet_lead import router as google_sheet_router
from app.web.health import router as health_router
from app.web.preland_tracking import router as tracking_router


def create_app(bot: Bot | None = None) -> FastAPI:
    app = FastAPI(title="Apex Lead Router")
    app.state.bot = bot
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(facebook_router)
    app.include_router(funnel_router)
    app.include_router(google_sheet_router)
    app.include_router(tracking_router)
    return app
