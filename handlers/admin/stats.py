import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin_kb import (
    StatsCb, MenuCb,
    stats_section_kb, select_client_for_stats_kb,
    select_offer_for_stats_kb, select_form_for_stats_kb, back_to_menu_kb,
)
from services.stats_service import (
    get_global_stats, get_client_stats, get_offer_stats, get_form_stats, get_ref_stats,
)
from services.client_service import get_clients_paginated
from services.offer_service import get_offers_paginated
from services.form_service import get_forms_paginated
from models.lead import LEAD_STATUS_LABELS

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(StatsCb.filter(F.action == "global"))
async def stats_global(callback: CallbackQuery, session: AsyncSession) -> None:
    s = await get_global_stats(session)
    text = (
        "📊 <b>Общая статистика</b>\n\n"
        f"📥 Всего лидов: <b>{s['total']}</b>\n"
        f"📅 Сегодня: <b>{s['today']}</b>\n"
        f"📅 За 7 дней: <b>{s['week']}</b>\n"
        f"📅 За 30 дней: <b>{s['month']}</b>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(StatsCb.filter(F.action == "select_client"))
async def stats_select_client(callback: CallbackQuery, session: AsyncSession) -> None:
    clients, _ = await get_clients_paginated(session, 0, 50)
    if not clients:
        await callback.answer("Клиентов нет.", show_alert=True)
        return
    await callback.message.edit_text(
        "📊 Выберите клиента для статистики:",
        reply_markup=select_client_for_stats_kb(clients),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(StatsCb.filter(F.action == "client"))
async def stats_client(callback: CallbackQuery, callback_data: StatsCb, session: AsyncSession) -> None:
    from services.client_service import get_client_by_id
    client = await get_client_by_id(session, callback_data.id)
    if not client:
        await callback.answer("Клиент не найден", show_alert=True)
        return
    s = await get_client_stats(session, callback_data.id)
    text = (
        f"📊 <b>Статистика клиента «{client.name}»</b>\n\n"
        f"📥 Всего: <b>{s['total']}</b>\n"
        f"📅 Сегодня: <b>{s['today']}</b>\n"
        f"📅 7 дней: <b>{s['week']}</b>\n"
        f"📅 30 дней: <b>{s['month']}</b>\n"
    )
    if s["best_offers"]:
        text += "\n🏆 <b>Топ офферы:</b>\n"
        for item in s["best_offers"]:
            text += f"  • {item['name']}: {item['count']}\n"
    if s["best_sources"]:
        text += "\n🔗 <b>Топ источники:</b>\n"
        for item in s["best_sources"]:
            text += f"  • {item['name']}: {item['count']}\n"
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(StatsCb.filter(F.action == "select_offer"))
async def stats_select_offer(callback: CallbackQuery, session: AsyncSession) -> None:
    offers, _ = await get_offers_paginated(session, 0, 50)
    if not offers:
        await callback.answer("Офферов нет.", show_alert=True)
        return
    await callback.message.edit_text(
        "📊 Выберите оффер:",
        reply_markup=select_offer_for_stats_kb(offers),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(StatsCb.filter(F.action == "offer"))
async def stats_offer(callback: CallbackQuery, callback_data: StatsCb, session: AsyncSession) -> None:
    from services.offer_service import get_offer_by_id
    offer = await get_offer_by_id(session, callback_data.id)
    if not offer:
        await callback.answer("Оффер не найден", show_alert=True)
        return
    s = await get_offer_stats(session, callback_data.id)
    text = (
        f"📊 <b>Статистика оффера «{offer.name}»</b>\n\n"
        f"📥 Всего лидов: <b>{s['total']}</b>\n"
    )
    if s["by_forms"]:
        text += "\n📝 <b>По формам:</b>\n"
        for item in s["by_forms"]:
            text += f"  • {item['name']}: {item['count']}\n"
    if s["by_sources"]:
        text += "\n🔗 <b>По источникам:</b>\n"
        for item in s["by_sources"]:
            text += f"  • {item['name']}: {item['count']}\n"
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(StatsCb.filter(F.action == "select_form"))
async def stats_select_form(callback: CallbackQuery, session: AsyncSession) -> None:
    forms, _ = await get_forms_paginated(session, 0, 50)
    if not forms:
        await callback.answer("Форм нет.", show_alert=True)
        return
    await callback.message.edit_text(
        "📊 Выберите форму:",
        reply_markup=select_form_for_stats_kb(forms),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(StatsCb.filter(F.action == "form"))
async def stats_form(callback: CallbackQuery, callback_data: StatsCb, session: AsyncSession) -> None:
    from services.form_service import get_form_by_id
    form = await get_form_by_id(session, callback_data.id)
    if not form:
        await callback.answer("Форма не найдена", show_alert=True)
        return
    s = await get_form_stats(session, callback_data.id)
    text = (
        f"📊 <b>Статистика формы «{form.name}»</b>\n\n"
        f"📥 Всего лидов: <b>{s['total']}</b>\n"
    )
    if s["by_sources"]:
        text += "\n🔗 <b>По источникам:</b>\n"
        for item in s["by_sources"]:
            text += f"  • {item['name']}: {item['count']}\n"
    if s["by_status"]:
        text += "\n🏷 <b>По статусам:</b>\n"
        for status, cnt in s["by_status"].items():
            label = LEAD_STATUS_LABELS.get(status, status)
            text += f"  • {label}: {cnt}\n"
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(StatsCb.filter(F.action == "ref"))
async def stats_ref(callback: CallbackQuery, callback_data: StatsCb, session: AsyncSession) -> None:
    from services.referral_service import get_ref_by_id
    ref = await get_ref_by_id(session, callback_data.id)
    if not ref:
        await callback.answer("Рефка не найдена", show_alert=True)
        return
    s = await get_ref_stats(session, callback_data.id)
    last = s["last_lead_at"]
    last_str = last.strftime("%d.%m.%Y %H:%M") if last else "—"
    text = (
        f"📊 <b>Статистика рефки «{ref.name}»</b>\n\n"
        f"📥 Всего лидов: <b>{s['total']}</b>\n"
        f"📅 Последний лид: {last_str}\n"
    )
    if s["by_status"]:
        text += "\n🏷 <b>По статусам:</b>\n"
        for status, cnt in s["by_status"].items():
            label = LEAD_STATUS_LABELS.get(status, status)
            text += f"  • {label}: {cnt}\n"
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()
