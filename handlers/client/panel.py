"""Client panel handlers (client_admin + client_viewer)."""
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.client_kb import ClCb, client_home_kb, client_stats_period_kb
from keyboards.client_kb import client_leads_kb, client_lead_view_kb, client_links_kb
from models.bot_user import BotUser
from models.lead import Lead, LEAD_STATUS_LABELS
from services.client_service import get_client_by_id
from services.lead_service import get_leads_paginated, update_lead_status
from services.referral_service import get_refs_by_form
from services.form_service import get_forms_paginated
from utils.pagination import PageResult
from config import PAGE_SIZE

logger = logging.getLogger(__name__)
router = Router()


def _check_client_access(bot_user: BotUser | None, client_id: int) -> bool:
    """Return True if bot_user may access data for this client_id."""
    if bot_user is None:
        return False
    return bot_user.client_id == client_id


async def _get_client_refs(session: AsyncSession, client_id: int) -> list:
    """Get all referral sources for all forms belonging to this client."""
    forms, _ = await get_forms_paginated(session, client_id=client_id, page_size=100)
    refs = []
    for form in forms:
        form_refs = await get_refs_by_form(session, form.id)
        refs.extend(form_refs)
    return refs


# ══════════════════════════════════════════════════════════════════════════════
# Home
# ══════════════════════════════════════════════════════════════════════════════

async def _show_client_home(
    callback: CallbackQuery, session: AsyncSession, bot_user: BotUser
) -> None:
    client_id = bot_user.client_id
    client = await get_client_by_id(session, client_id)
    can_change = bot_user.role == "client_admin"

    # Quick stats for today
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    from datetime import datetime as dt
    from models.lead import Lead
    q = (
        select(Lead.status, func.count().label("cnt"))
        .where(and_(Lead.client_id == client_id, func.date(Lead.created_at) == today))
        .group_by(Lead.status)
    )
    rows = (await session.execute(q)).all()
    statuses = {r.status: r.cnt for r in rows}

    total = sum(statuses.values())
    new_cnt = statuses.get("new", 0)
    working_cnt = statuses.get("contacted", 0) + statuses.get("qualified", 0)
    approved_cnt = statuses.get("approved", 0)

    # Best source (all-time, by approved leads count)
    from models.referral_source import ReferralSource
    best_q = (
        select(ReferralSource.name, func.count(Lead.id).label("cnt"))
        .join(Lead, Lead.referral_source_id == ReferralSource.id)
        .where(and_(Lead.client_id == client_id, Lead.status == "approved"))
        .group_by(ReferralSource.name)
        .order_by(func.count(Lead.id).desc())
        .limit(1)
    )
    best_row = (await session.execute(best_q)).first()
    best_src = f"{best_row.name} — {best_row.cnt} approved" if best_row else "—"

    client_name = client.name if client else f"Клиент #{client_id}"
    text = (
        f"🏠 <b>Кабинет клиента</b>\n\n"
        f"<b>{client_name}</b>\n"
        f"Период: сегодня\n\n"
        f"Заявки сегодня: <b>{total}</b>\n"
        f"Новые:          <b>{new_cnt}</b>\n"
        f"В работе:       <b>{working_cnt}</b>\n"
        f"Approved:       <b>{approved_cnt}</b>\n\n"
        f"Лучший источник:\n{best_src}\n\n"
        f"<i>Что открыть?</i>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=client_home_kb(can_change_status=can_change),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ClCb.filter(F.section == "home"))
async def client_home(
    callback: CallbackQuery, session: AsyncSession, bot_user: BotUser
) -> None:
    if not bot_user or not bot_user.client_id:
        await callback.answer("Нет данных клиента", show_alert=True)
        return
    await _show_client_home(callback, session, bot_user)


# ══════════════════════════════════════════════════════════════════════════════
# Stats
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(ClCb.filter(F.section == "stats"))
async def client_stats(
    callback: CallbackQuery, callback_data: ClCb, session: AsyncSession, bot_user: BotUser
) -> None:
    if not bot_user or not bot_user.client_id:
        await callback.answer("Нет доступа", show_alert=True)
        return
    client_id = bot_user.client_id
    days = callback_data.days or 7

    from datetime import datetime as dt
    date_from = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    q = (
        select(Lead.status, func.count().label("cnt"))
        .where(and_(
            Lead.client_id == client_id,
            func.date(Lead.created_at) >= date_from,
        ))
        .group_by(Lead.status)
    )
    rows = (await session.execute(q)).all()
    statuses = {r.status: r.cnt for r in rows}

    total = sum(statuses.values())
    new_cnt = statuses.get("new", 0)
    contacted = statuses.get("contacted", 0)
    qualified = statuses.get("qualified", 0)
    approved = statuses.get("approved", 0)

    comp_rate = f"{round(total / max(total, 1) * 100)}%"
    apr_rate = f"{round(approved / max(total, 1) * 100, 1)}%"

    period_label = {1: "Сегодня", 7: "7 дней", 30: "30 дней"}.get(days, f"{days}д")
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"Период: <b>{period_label}</b>\n\n"
        f"Заявки:    <b>{total}</b>\n"
        f"Новые:     <b>{new_cnt}</b>\n"
        f"Contacted: <b>{contacted}</b>\n"
        f"Qualified: <b>{qualified}</b>\n"
        f"Approved:  <b>{approved}</b>\n\n"
        f"Approve rate: <b>{apr_rate}</b>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=client_stats_period_kb(days),
        parse_mode="HTML",
    )
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
# Leads list
# ══════════════════════════════════════════════════════════════════════════════

_STATUS_FILTER_MAP = {0: None, 1: "contacted", 2: "approved", 3: "rejected"}


@router.callback_query(ClCb.filter(F.section == "leads"))
async def client_leads(
    callback: CallbackQuery, callback_data: ClCb, session: AsyncSession, bot_user: BotUser
) -> None:
    if not bot_user or not bot_user.client_id:
        await callback.answer("Нет доступа", show_alert=True)
        return
    client_id = bot_user.client_id
    page = callback_data.page
    status_key = callback_data.id
    status_filter = _STATUS_FILTER_MAP.get(status_key)
    if status_key == 0 and status_filter is None:
        status_filter = "new"

    filters = {"client_id": client_id}
    if status_filter:
        filters["status"] = status_filter

    items, total = await get_leads_paginated(session, page, PAGE_SIZE, filters=filters)
    pr = PageResult(items=items, total=total, page=page, page_size=PAGE_SIZE)

    status_label = {
        None: "Все", "new": "Новые", "contacted": "В работе",
        "approved": "Approved", "rejected": "Rejected",
    }.get(status_filter, "Все")

    await callback.message.edit_text(
        f"📥 <b>Мои заявки</b>\n\n"
        f"Фильтр: <b>{status_label}</b>  Найдено: <b>{total}</b>",
        reply_markup=client_leads_kb(items, pr, current_status=status_filter or ""),
        parse_mode="HTML",
    )
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
# Lead view
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(ClCb.filter(F.section == "lead"))
async def client_lead_view(
    callback: CallbackQuery, callback_data: ClCb, session: AsyncSession, bot_user: BotUser
) -> None:
    if not bot_user or not bot_user.client_id:
        await callback.answer("Нет доступа", show_alert=True)
        return

    lead = await session.get(Lead, callback_data.id)
    if not lead or lead.client_id != bot_user.client_id:
        await callback.answer("Заявка не найдена или нет доступа", show_alert=True)
        return

    import json
    answers_raw = lead.answers_json or "{}"
    try:
        answers = json.loads(answers_raw)
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

    if lead.notes:
        lines.append(f"\n📝 Заметка: {lead.notes}")

    can_change = bot_user.role == "client_admin"
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=client_lead_view_kb(lead.id, callback_data.page, can_change=can_change),
        parse_mode="HTML",
    )
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
# Status change (client_admin only)
# ══════════════════════════════════════════════════════════════════════════════

_CLIENT_STATUS_MAP = {1: "contacted", 2: "approved", 3: "rejected"}


@router.callback_query(ClCb.filter(F.section == "status"))
async def client_set_status(
    callback: CallbackQuery, callback_data: ClCb, session: AsyncSession, bot_user: BotUser
) -> None:
    if not bot_user or bot_user.role != "client_admin":
        await callback.answer("Нет прав для изменения статуса", show_alert=True)
        return

    lead = await session.get(Lead, callback_data.id)
    if not lead or lead.client_id != bot_user.client_id:
        await callback.answer("Заявка не найдена или нет доступа", show_alert=True)
        return

    new_status = _CLIENT_STATUS_MAP.get(callback_data.page)
    if not new_status:
        await callback.answer("Неверный статус", show_alert=True)
        return

    await update_lead_status(session, lead.id, new_status)
    await session.commit()

    label = LEAD_STATUS_LABELS.get(new_status, new_status)
    await callback.answer(f"✅ Статус изменён: {label}", show_alert=False)
    # Refresh lead view
    view_cb = ClCb(section="lead", id=lead.id)
    await client_lead_view(callback, view_cb, session, bot_user)


# ══════════════════════════════════════════════════════════════════════════════
# Links (referral sources)
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(ClCb.filter(F.section == "links"))
async def client_links(
    callback: CallbackQuery, session: AsyncSession, bot_user: BotUser
) -> None:
    if not bot_user or not bot_user.client_id:
        await callback.answer("Нет доступа", show_alert=True)
        return
    refs = await _get_client_refs(session, bot_user.client_id)
    await callback.message.edit_text(
        f"🔗 <b>Мои ссылки</b>\n\nАктивных источников: <b>{len([r for r in refs if r.status == 'active'])}</b>\n\n"
        f"Выбери источник для копирования ссылки:",
        reply_markup=client_links_kb(refs),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ClCb.filter(F.section == "link_view"))
async def client_link_view(
    callback: CallbackQuery, callback_data: ClCb, session: AsyncSession, bot_user: BotUser
) -> None:
    from services.referral_service import get_ref_by_id, build_start_link
    ref = await get_ref_by_id(session, callback_data.id)
    if not ref:
        await callback.answer("Источник не найден", show_alert=True)
        return
    # Verify this ref belongs to client
    from services.form_service import get_form_by_id
    form = await get_form_by_id(session, ref.form_id)
    if not form or form.client_id != bot_user.client_id:
        await callback.answer("Нет доступа", show_alert=True)
        return

    link = build_start_link(ref.form_id, ref.code)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="◀️ К ссылкам", callback_data=ClCb(section="links"))
    b.button(text="🏠 Кабинет",   callback_data=ClCb(section="home"))
    b.adjust(1)

    await callback.message.edit_text(
        f"🔗 <b>{ref.name}</b>\n\n"
        f"Ссылка:\n<code>{link}</code>\n\n"
        f"<i>Зажми ссылку, чтобы скопировать.</i>",
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
# Export (basic CSV link via export_section)
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(ClCb.filter(F.section == "export"))
async def client_export(
    callback: CallbackQuery, session: AsyncSession, bot_user: BotUser
) -> None:
    if not bot_user or not bot_user.client_id:
        await callback.answer("Нет доступа", show_alert=True)
        return
    from services.export_service import export_leads
    from aiogram.types import BufferedInputFile
    import io

    file_bytes = await export_leads(session, fmt="xlsx", client_id=bot_user.client_id)
    buf = BufferedInputFile(file_bytes, filename="leads.xlsx")
    await callback.message.answer_document(buf, caption="📤 Ваши заявки (XLSX)")
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
# Contact (sends message to admin / super_admin)
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(ClCb.filter(F.section == "contact"))
async def client_contact(callback: CallbackQuery) -> None:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="🏠 Кабинет", callback_data=ClCb(section="home"))
    await callback.message.edit_text(
        "👤 <b>Связаться с менеджером</b>\n\n"
        "Напишите напрямую вашему менеджеру или\n"
        "отправьте сообщение администратору системы.",
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()
