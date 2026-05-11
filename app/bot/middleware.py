from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import ADMIN_IDS
from database import AsyncSessionLocal


class IgnoreNotModifiedMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except TelegramBadRequest as exc:
            msg = str(exc).lower()
            if "message is not modified" in msg or "message to edit not found" in msg:
                cb = getattr(event, "callback_query", None) or (event if isinstance(event, CallbackQuery) else None)
                if cb is not None:
                    try:
                        await cb.answer()
                    except Exception:
                        pass
                return None
            raise


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with AsyncSessionLocal() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise


class AdminAwareMiddleware(BaseMiddleware):
    """
    Sets data["is_admin"] based on ADMIN_IDS fallback OR admins table.
    Does NOT block non-admin users — clients need full bot access.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from app.services.admin_service import is_admin_in_db  # lazy import avoids circular

        user = data.get("event_from_user")
        is_admin = False
        if user:
            if ADMIN_IDS and user.id in ADMIN_IDS:
                is_admin = True
            elif not is_admin:
                # Check DB — session is already set by DatabaseMiddleware (runs first)
                session = data.get("session")
                if session is not None:
                    try:
                        is_admin = await is_admin_in_db(session, user.id)
                    except Exception:
                        is_admin = False

        data["is_admin"] = is_admin

        if isinstance(event, CallbackQuery) and not is_admin:
            callback_data = event.data or ""
            admin_prefixes = (
                "funnel:",
                "leads:",
                "prelands:",
                "settings:",
                "stats:",
                "wizard:",
            )
            if callback_data.startswith(admin_prefixes):
                await event.answer("Нет доступа.", show_alert=True)
                return None

        return await handler(event, data)


# Keep alias so existing imports still work
AdminOnlyMiddleware = AdminAwareMiddleware
