"""
handlers/shared/start.py — role-aware /start handler.

This router has NO middleware — it handles /start for ALL user types and routes
to the appropriate panel based on the injected user_role.

First-user logic:
    If no super_admin exists in the database yet, the very first person who
    sends /start is automatically promoted to super_admin and stored in DB.
"""
import logging
from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import BOT_USERNAME
from keyboards.admin_kb import main_menu_kb
from services.today_service import get_today_dashboard
from services.user_service import list_bot_users, create_bot_user

logger = logging.getLogger(__name__)
router = Router()

_SITE_ID = "skyx_pl_1830"


def _fmt_admin_home(data: dict) -> str:
    date = data["date"]
    total = data["total_leads"]
    statuses = data["statuses"]
    funnel = data["funnel"]
    best = data.get("best")
    worst = data.get("worst")

    new = statuses.get("new", 0)
    qualified = statuses.get("qualified", 0)
    approved = statuses.get("approved", 0)
    duplicates = funnel.get("duplicates", 0)

    lines = [
        "🏠 <b>ApexNotification</b>",
        "",
        f"<b>Сегодня {date}:</b>",
        f"Лиды:     <b>{total}</b>",
        f"Новые:    <b>{new}</b>",
        f"Qualified: <b>{qualified}</b>",
        f"Approved: <b>{approved}</b>",
    ]
    if duplicates:
        lines.append(f"Дубли:    {duplicates}")

    if best and best.get("leads"):
        rate = (
            f"{round(best['approved'] / best['leads'] * 100)}%"
            if best["leads"]
            else "0%"
        )
        lines.append("")
        lines.append(
            f"🔥 <b>Лучший:</b> {best['name']} — {best['leads']}L / {best['approved']}A / {rate}"
        )

    if worst and worst.get("starts"):
        lines.append("")
        lines.append(
            f"⚠️ <b>Проблема:</b> {worst['name']} — {worst['starts']} стартов / {worst['leads']} лидов"
        )

    if not total:
        lines.append("")
        lines.append("<i>Данных за сегодня пока нет.</i>")

    lines.append("")
    lines.append("<i>Что делаем?</i>")
    return "\n".join(lines)


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_role: str = "anonymous",
    bot_user=None,
) -> None:
    await state.clear()

    # ── First-user auto-promotion ──────────────────────────────────────────────
    # If nobody is super_admin yet in the DB, the very first /start makes this
    # user super_admin permanently.
    if user_role == "anonymous":
        existing_admins = await list_bot_users(session, role="super_admin")
        if not existing_admins:
            tg_user = message.from_user
            try:
                bot_user = await create_bot_user(
                    session,
                    tg_id=tg_user.id,
                    username=tg_user.username,
                    role="super_admin",
                )
                await session.commit()
                user_role = "super_admin"
                logger.info(
                    "First-user super_admin created: tg_id=%s username=%s",
                    tg_user.id, tg_user.username,
                )
            except IntegrityError:
                # Race condition: another concurrent /start already created the user
                await session.rollback()
                admins = await list_bot_users(session, role="super_admin")
                if admins:
                    for a in admins:
                        if a.telegram_user_id == tg_user.id:
                            bot_user = a
                            user_role = "super_admin"
                            break

    # ── Route by role ─────────────────────────────────────────────────────────
    if user_role == "super_admin":
        try:
            today = await get_today_dashboard(session, site_id=_SITE_ID)
            text = _fmt_admin_home(today)
        except Exception:
            text = "🏠 <b>ApexNotification</b>\n\n<i>Что делаем?</i>"
        await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")
        return

    if user_role in ("client_admin", "client_viewer"):
        from keyboards.client_kb import client_home_kb
        can_change = user_role == "client_admin"
        await message.answer(
            "🏠 <b>Кабинет клиента</b>\n\nВыберите раздел:",
            reply_markup=client_home_kb(can_change_status=can_change),
            parse_mode="HTML",
        )
        return

    if user_role == "manager":
        from keyboards.manager_kb import manager_home_kb
        await message.answer(
            "🏠 <b>Кабинет менеджера</b>\n\nЧто обрабатываем?",
            reply_markup=manager_home_kb(),
            parse_mode="HTML",
        )
        return

    # Anonymous with existing admins — not authorised
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Для доступа к панели обратитесь к администратору.",
        parse_mode="HTML",
    )
