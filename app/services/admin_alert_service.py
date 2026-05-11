from __future__ import annotations

import logging
from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from config import ADMIN_IDS

logger = logging.getLogger(__name__)


async def get_admin_chat_ids(session: AsyncSession) -> list[int]:
    ids: set[int] = set(ADMIN_IDS)
    try:
        rows = await session.execute(select(Admin.telegram_user_id))
        ids.update(int(x) for x in rows.scalars().all() if x)
    except Exception:
        logger.exception("Failed to load admins for alert")
    return sorted(ids)


async def notify_admins(
    session: AsyncSession,
    bot: Bot | None,
    text: str,
) -> None:
    if bot is None:
        return
    chat_ids = await get_admin_chat_ids(session)
    if not chat_ids:
        logger.warning("Admin alert skipped: no admins configured")
        return
    body = "<b>Apex Lead Router ALERT</b>\n\n" + text
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id, body, disable_web_page_preview=True)
        except Exception:
            logger.exception("Failed to send admin alert to %s", chat_id)
