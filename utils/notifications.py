import logging
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from config import ADMIN_IDS
from models.lead import Lead
from utils.formatters import fmt_lead

logger = logging.getLogger(__name__)


async def notify_admins_new_lead(bot: Bot, lead: Lead) -> None:
    text = f"🔔 <b>Новый лид!</b>\n\n{fmt_lead(lead)}"
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML")
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.warning("Cannot notify admin %s: %s", admin_id, e)
        except Exception as e:
            logger.error("Unexpected error notifying admin %s: %s", admin_id, e)
