from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from config import ADMIN_IDS


class AdminMiddleware(BaseMiddleware):
    """Allow only super_admin (injected by RoleMiddleware) to access admin routers.

    Falls back to ADMIN_IDS check if RoleMiddleware has not run yet.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        user_role = data.get("user_role")
        if user_role is None:
            # Fallback: RoleMiddleware not registered, check ADMIN_IDS directly
            user = data.get("event_from_user")
            user_role = "super_admin" if (user and user.id in ADMIN_IDS) else "anonymous"

        if user_role != "super_admin":
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Нет доступа.", show_alert=True)
            elif isinstance(event, Message):
                await event.answer("⛔ У вас нет доступа к этому боту.")
            return
        return await handler(event, data)


class ClientMiddleware(BaseMiddleware):
    """Allow client_admin and client_viewer roles only."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        user_role = data.get("user_role", "anonymous")
        if user_role not in ("client_admin", "client_viewer"):
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Нет доступа.", show_alert=True)
            return
        return await handler(event, data)


class ManagerMiddleware(BaseMiddleware):
    """Allow manager role only."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        user_role = data.get("user_role", "anonymous")
        if user_role != "manager":
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Нет доступа.", show_alert=True)
            return
        return await handler(event, data)
