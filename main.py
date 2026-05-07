"""
Entry point for the LeadForm Hub Telegram bot.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, LOG_LEVEL, DATABASE_URL, ADMIN_IDS
from database import init_db
from middlewares import AdminMiddleware, ClientMiddleware, ManagerMiddleware, DatabaseMiddleware, RoleMiddleware

# Admin handlers
from handlers.admin import (
    menu_router,
    today_router,
    clients_router,
    offers_router,
    forms_router,
    questions_router,
    refs_router,
    leads_router,
    stats_router,
    exports_router,
    conversions_router,
    wizard_router,
    pixels_router,
)
# User flow handler
from handlers.user import user_flow_router
# Shared (role-aware /start)
from handlers.shared import shared_router
# Client panel
from handlers.client import client_router
# Manager panel
from handlers.manager import manager_router

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("=== LeadForm Hub starting ===")
    logger.info("Database URL: %s", DATABASE_URL)
    logger.info("Admin IDs: %s", ADMIN_IDS)

    try:
        await init_db()
        logger.info("Database initialised successfully.")
    except Exception as exc:
        logger.critical("Failed to initialise database: %s", exc, exc_info=True)
        raise

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # ── Global middleware ─────────────────────────────────────────────────────
    # DatabaseMiddleware must be first (provides session)
    dp.update.outer_middleware(DatabaseMiddleware())
    # RoleMiddleware uses the session to resolve user roles
    dp.update.outer_middleware(RoleMiddleware())

    # ── User flow router (no auth, handles lf_ deep links) ───────────────────
    dp.include_router(user_flow_router)

    # ── Shared router (role-aware /start, no auth middleware) ─────────────────
    dp.include_router(shared_router)

    # ── Admin routers (protected by AdminMiddleware) ──────────────────────────
    for admin_router in [
        menu_router,
        today_router,
        clients_router,
        offers_router,
        forms_router,
        questions_router,
        refs_router,
        leads_router,
        stats_router,
        exports_router,
        conversions_router,
        wizard_router,
        pixels_router,
    ]:
        admin_router.message.outer_middleware(AdminMiddleware())
        admin_router.callback_query.outer_middleware(AdminMiddleware())
        dp.include_router(admin_router)

    # ── Client panel (client_admin + client_viewer) ───────────────────────────
    client_router.message.outer_middleware(ClientMiddleware())
    client_router.callback_query.outer_middleware(ClientMiddleware())
    dp.include_router(client_router)

    # ── Manager panel ─────────────────────────────────────────────────────────
    manager_router.message.outer_middleware(ManagerMiddleware())
    manager_router.callback_query.outer_middleware(ManagerMiddleware())
    dp.include_router(manager_router)

    logger.info("Starting polling … (drop_pending_updates=True)")
    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    except Exception as exc:
        logger.critical("Polling crashed: %s", exc, exc_info=True)
        raise
    finally:
        logger.info("Shutting down, closing bot session.")
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
