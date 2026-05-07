"""RoleMiddleware — injects user_role and bot_user into handler data."""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from config import ADMIN_IDS
from services.user_service import get_bot_user


class RoleMiddleware(BaseMiddleware):
    """
    Must be registered AFTER DatabaseMiddleware so that data["session"] is
    already available.

    Injects:
        data["user_role"]: str  — "super_admin" | "client_admin" |
                                   "client_viewer" | "manager" | "anonymous"
        data["bot_user"]:  BotUser | None
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        user = data.get("event_from_user")

        if user is None:
            data["user_role"] = "anonymous"
            data["bot_user"] = None
            return await handler(event, data)

        # Super-admins are identified by ADMIN_IDS in config — no DB lookup needed
        if user.id in ADMIN_IDS:
            data["user_role"] = "super_admin"
            data["bot_user"] = None
            return await handler(event, data)

        # For everyone else, look up BotUser record
        session = data.get("session")
        bot_user = None
        if session is not None:
            try:
                bot_user = await get_bot_user(session, user.id)
            except Exception:
                pass

        if bot_user and bot_user.is_active:
            data["user_role"] = bot_user.role
            data["bot_user"] = bot_user
        else:
            data["user_role"] = "anonymous"
            data["bot_user"] = None

        return await handler(event, data)
