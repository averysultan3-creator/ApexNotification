import asyncio
import logging
import os
import pathlib
import sys

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

try:
    from aiogram.client.default import DefaultBotProperties
except ImportError:  # aiogram 3.0 compatibility in older server envs
    DefaultBotProperties = None

from app.bot.handlers import routers
from app.bot.middleware import AdminOnlyMiddleware, DatabaseMiddleware, IgnoreNotModifiedMiddleware
from app.web.api import create_app
from config import ADMIN_IDS, BOT_TOKEN, DATABASE_URL, LOG_LEVEL, WEB_HOST, WEB_PORT
from database import init_db


pathlib.Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/server.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    if DefaultBotProperties is None:
        return Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    return Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.outer_middleware(IgnoreNotModifiedMiddleware())
    dp.update.outer_middleware(DatabaseMiddleware())
    dp.update.outer_middleware(AdminOnlyMiddleware())
    for router in routers:
        dp.include_router(router)
    return dp


async def run_bot() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is required for bot mode.")
    if not ADMIN_IDS:
        logger.warning("ADMIN_IDS is empty; admin Telegram menu will be unavailable.")

    logger.info("Apex Lead Router bot starting. DB: %s", DATABASE_URL)
    await init_db()
    bot = create_bot()
    dp = create_dispatcher()
    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    finally:
        await bot.session.close()


async def run_web(bot: Bot | None = None) -> None:
    logger.info("Apex Lead Router web starting on %s:%s. DB: %s", WEB_HOST, WEB_PORT, DATABASE_URL)
    await init_db()
    app = create_app(bot=bot)
    config = uvicorn.Config(app, host=WEB_HOST, port=WEB_PORT, log_level=LOG_LEVEL.lower())
    server = uvicorn.Server(config)
    await server.serve()


async def run_all() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is required for all mode.")
    if not ADMIN_IDS:
        logger.warning("ADMIN_IDS is empty; admin Telegram menu will be unavailable.")

    logger.info("Apex Lead Router starting in all mode. DB: %s", DATABASE_URL)
    await init_db()
    bot = create_bot()
    dp = create_dispatcher()
    app = create_app(bot=bot)
    server = uvicorn.Server(uvicorn.Config(app, host=WEB_HOST, port=WEB_PORT, log_level=LOG_LEVEL.lower()))

    try:
        done, pending = await asyncio.wait(
            [
                asyncio.create_task(dp.start_polling(bot, drop_pending_updates=True), name="bot"),
                asyncio.create_task(server.serve(), name="web"),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )
        # One task finished (crashed or stopped) — cancel the other and exit
        for task in pending:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        # Re-raise exception from finished task if any
        for task in done:
            if task.exception():
                raise task.exception()
    finally:
        await bot.session.close()


async def main() -> None:
    # Write PID so WATCHDOG can monitor the process
    pathlib.Path("runtime").mkdir(exist_ok=True)
    pid_file = pathlib.Path("runtime/server.pid")
    pid_file.write_text(str(os.getpid()))

    try:
        mode = (sys.argv[1] if len(sys.argv) > 1 else "bot").lower()
        if mode == "bot":
            await run_bot()
        elif mode == "web":
            await run_web()
        elif mode == "all":
            await run_all()
        else:
            raise SystemExit("Usage: python main.py [bot|web|all]")
    finally:
        try:
            if pid_file.read_text().strip() == str(os.getpid()):
                pid_file.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
