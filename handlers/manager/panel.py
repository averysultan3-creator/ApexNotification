"""Manager panel handlers."""
import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.manager_kb import MgrCb, manager_home_kb, manager_leads_kb, manager_lead_view_kb
from models.bot_user import BotUser
from models.lead import Lead, LEAD_STATUS_LABELS
from services.lead_service import get_leads_paginated, update_lead_status
from utils.pagination import PageResult
from config import PAGE_SIZE

logger = logging.getLogger(__name__)
router = Router()

_STATUS_KEYS = {
    "new": "new",
    "working": "contacted",
    "approved": "approved",
}
_STATUS_ACTIONS = {1: "contacted", 2: "qualified", 3: "approved", 4: "rejected"}


@router.callback_query(MgrCb.filter(F.section == "home"))
async def mgr_home(callback: CallbackQuery, bot_user: BotUser) -> None:
    await callback.message.edit_text(
        "🏠 <b>Кабинет менеджера</b>\n\nЧто обрабатываем?",
        reply_markup=manager_home_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(MgrCb.filter(F.section.in_({"new", "working", "approved"})))
async def mgr_leads(
    callback: CallbackQuery, callback_data: MgrCb, session: AsyncSession, bot_user: BotUser
) -> None:
    section = callback_data.section
    status = _STATUS_KEYS.get(section, "new")
    page = callback_data.page

    # Managers see ALL leads with this status (or only assigned — extend later)
    items, total = await get_leads_paginated(
        session, page, PAGE_SIZE, filters={"status": status}
    )
    pr = PageResult(items=items, total=total, page=page, page_size=PAGE_SIZE)

    labels = {"new": "Новые", "working": "В работе", "approved": "Approved"}
    await callback.message.edit_text(
        f"📥 <b>{labels.get(section, section)}</b>  (всего: {total})",
        reply_markup=manager_leads_kb(items, pr, status=section),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(MgrCb.filter(F.section == "lead"))
async def mgr_lead_view(
    callback: CallbackQuery, callback_data: MgrCb, session: AsyncSession, bot_user: BotUser
) -> None:
    lead = await session.get(Lead, callback_data.id)
    if not lead:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    import json
    try:
        answers = json.loads(lead.answers_json or "{}")
    except Exception:
        answers = {}

    status_label = LEAD_STATUS_LABELS.get(lead.status, lead.status)
    date_fmt = lead.created_at.strftime("%d.%m.%Y %H:%M") if lead.created_at else "—"

    lines = [
        f"📥 <b>Заявка #{lead.id}</b>\n",
        f"Статус: <b>{status_label}</b>",
        f"Дата:   {date_fmt}",
    ]
    if lead.telegram_username:
        lines.append(f"Telegram: @{lead.telegram_username}")

    if answers:
        lines.append("\n<b>Ответы:</b>")
        for q, a in answers.items():
            lines.append(f"{q}: {a}")

    # Determine which "back" section to use
    back_section = {
        "new": "new", "contacted": "working",
        "qualified": "working", "approved": "approved",
    }.get(lead.status, "new")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=manager_lead_view_kb(lead.id, callback_data.page, status=back_section),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(MgrCb.filter(F.section == "status"))
async def mgr_set_status(
    callback: CallbackQuery, callback_data: MgrCb, session: AsyncSession, bot_user: BotUser
) -> None:
    lead = await session.get(Lead, callback_data.id)
    if not lead:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    new_status = _STATUS_ACTIONS.get(callback_data.page)
    if not new_status:
        await callback.answer("Неверный статус", show_alert=True)
        return

    await update_lead_status(session, lead.id, new_status)
    await session.commit()

    label = LEAD_STATUS_LABELS.get(new_status, new_status)
    await callback.answer(f"✅ {label}", show_alert=False)
    # Refresh lead view
    view_cb = MgrCb(section="lead", id=lead.id, page=callback_data.page)
    await mgr_lead_view(callback, view_cb, session, bot_user)


@router.callback_query(MgrCb.filter(F.section == "stats"))
async def mgr_stats(
    callback: CallbackQuery, session: AsyncSession, bot_user: BotUser
) -> None:
    from sqlalchemy import select, func
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    from models.lead import Lead
    from sqlalchemy import and_
    q = (
        select(Lead.status, func.count().label("cnt"))
        .where(func.date(Lead.created_at) == today)
        .group_by(Lead.status)
    )
    rows = (await session.execute(q)).all()
    statuses = {r.status: r.cnt for r in rows}

    total = sum(statuses.values())
    lines = [
        f"📊 <b>Моя статистика</b>",
        f"Сегодня:\n",
        f"Всего заявок: <b>{total}</b>",
    ]
    for status, cnt in sorted(statuses.items(), key=lambda x: -x[1]):
        label = LEAD_STATUS_LABELS.get(status, status)
        lines.append(f"{label}: <b>{cnt}</b>")

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="🏠 Кабинет", callback_data=MgrCb(section="home"))

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()
