import json

from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.leads_kb import lead_card_kb, leads_list_kb, leads_menu_kb
from app.services.lead_service import (
    get_lead_by_id,
    list_leads_all,
    list_leads_errors,
    list_leads_last_n,
    list_leads_today,
    list_leads_undelivered,
)
from app.utils.formatters import format_lead_card

router = Router(name="leads")


@router.callback_query(lambda c: c.data == "leads:menu")
async def leads_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    today = await list_leads_today(session)
    errors = [lead for lead in today if lead.delivery_error]
    await callback.message.edit_text(
        f"<b>📋 Лиды</b>\n\nСегодня: {len(today)}\nОшибок: {len(errors)}",
        reply_markup=leads_menu_kb(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "leads:today")
async def leads_today(callback: CallbackQuery, session: AsyncSession) -> None:
    leads = await list_leads_today(session)
    if not leads:
        await callback.answer("Сегодня лидов нет.", show_alert=True)
        return
    await callback.message.edit_text(
        f"Лиды за сегодня ({len(leads)}):",
        reply_markup=leads_list_kb(leads, back_cb="leads:menu"),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "leads:errors")
async def leads_errors(callback: CallbackQuery, session: AsyncSession) -> None:
    leads = await list_leads_errors(session)
    if not leads:
        await callback.answer("Ошибок доставки нет.", show_alert=True)
        return
    await callback.message.edit_text(
        f"Ошибки доставки ({len(leads)}):",
        reply_markup=leads_list_kb(leads, back_cb="leads:menu"),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "leads:last20")
async def leads_last20(callback: CallbackQuery, session: AsyncSession) -> None:
    leads = await list_leads_last_n(session, 20)
    if not leads:
        await callback.answer("Лидов ещё нет.", show_alert=True)
        return
    await callback.message.edit_text(
        f"Последние {len(leads)} лидов:",
        reply_markup=leads_list_kb(leads, back_cb="leads:menu"),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "leads:all")
async def leads_all(callback: CallbackQuery, session: AsyncSession) -> None:
    leads = await list_leads_all(session, limit=200)
    if not leads:
        await callback.answer("Лидов ещё нет.", show_alert=True)
        return
    await callback.message.edit_text(
        f"Все лиды ({len(leads)}):",
        reply_markup=leads_list_kb(leads, back_cb="leads:menu"),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "leads:undelivered")
async def leads_undelivered(callback: CallbackQuery, session: AsyncSession) -> None:
    leads = await list_leads_undelivered(session)
    if not leads:
        await callback.answer("Все лиды доставлены.", show_alert=True)
        return
    await callback.message.edit_text(
        f"Не доставлено ({len(leads)}):",
        reply_markup=leads_list_kb(leads, back_cb="leads:menu"),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("leads:card:"))
async def lead_card(callback: CallbackQuery, session: AsyncSession) -> None:
    lead_id = int(callback.data.split(":")[2])
    lead = await get_lead_by_id(session, lead_id)
    if not lead:
        await callback.answer("Лид не найден.", show_alert=True)
        return
    await callback.message.edit_text(format_lead_card(lead), reply_markup=lead_card_kb(lead.id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("leads:raw:"))
async def lead_raw(callback: CallbackQuery, session: AsyncSession) -> None:
    lead_id = int(callback.data.split(":")[2])
    lead = await get_lead_by_id(session, lead_id)
    if not lead:
        await callback.answer("Лид не найден.", show_alert=True)
        return
    raw = lead.raw_data_json or "{}"
    try:
        parsed = json.loads(raw)
        text = f"Raw #{lead.id}:\n<pre>{json.dumps(parsed, ensure_ascii=False, indent=2)[:3000]}</pre>"
    except Exception:
        text = f"Raw #{lead.id}:\n<pre>{raw[:3000]}</pre>"
    await callback.message.edit_text(text, reply_markup=lead_card_kb(lead.id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("leads:retry:"))
async def lead_retry(callback: CallbackQuery, session: AsyncSession) -> None:
    lead_id = int(callback.data.split(":")[2])
    lead = await get_lead_by_id(session, lead_id)
    if not lead:
        await callback.answer("Лид не найден.", show_alert=True)
        return
    from app.services.delivery_service import deliver_lead
    lead.delivered_telegram = False
    lead.delivered_sheet = False
    lead.delivery_error = None
    await deliver_lead(session, callback.bot, lead)
    await callback.message.edit_text(format_lead_card(lead), reply_markup=lead_card_kb(lead.id))
    await callback.answer("Delivery retried.")
