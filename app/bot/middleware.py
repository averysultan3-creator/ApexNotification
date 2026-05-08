from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import ADMIN_IDS
from database import AsyncSessionLocal


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


class AdminOnlyMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not ADMIN_IDS:
            return await handler(event, data)

        user = data.get("event_from_user")
        if user and user.id in ADMIN_IDS:
            return await handler(event, data)

        if isinstance(event, Message):
            await event.answer("Access denied.")
        elif isinstance(event, CallbackQuery):
            await event.answer("Access denied.", show_alert=True)
        return None
