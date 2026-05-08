import json

from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.leads_kb import lead_card_kb, leads_menu_kb
from app.bot.keyboards.main_kb import back_home_kb
from app.models.lead import Lead
from app.services.delivery_service import deliver_lead
from app.services.lead_service import get_lead_by_id, list_delivery_error_leads, list_leads, list_leads_today
from app.utils.formatters import format_lead_card

router = Router(name="leads")


@router.callback_query(lambda c: c.data == "leads:menu")
async def leads_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    today = await list_leads_today(session, limit=1_000)
    errors = await list_delivery_error_leads(session, limit=1_000)
    delivered = sum(1 for lead in today if lead.delivered_telegram or lead.delivered_email or lead.delivered_sheet)
    text = f"📥 <b>Лиды</b>\n\nСегодня: {len(today)}\nДоставлено: {delivered}\nОшибок: {len(errors)}"
    await callback.message.edit_text(text, reply_markup=leads_menu_kb())
    await callback.answer()


async def _show_leads(callback: CallbackQuery, leads: list[Lead], title: str) -> None:
    if not leads:
        await callback.message.edit_text(f"{title}\n\nПока пусто.", reply_markup=leads_menu_kb())
        return
    lines = [title, ""]
    for lead in leads[:20]:
        lines.append(f"#{lead.id} — {lead.full_name or lead.phone or lead.email or 'no name'}")
    lines.append("\nОткрой лид командой через карточку из списка в базе или нажми экспорт.")
    await callback.message.edit_text("\n".join(lines), reply_markup=leads_menu_kb())


@router.callback_query(lambda c: c.data in {"leads:today", "leads:all", "leads:errors"})
async def leads_lists(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.data == "leads:today":
        leads = await list_leads_today(session)
        title = "🆕 <b>Лиды сегодня</b>"
    elif callback.data == "leads:errors":
        leads = await list_delivery_error_leads(session)
        title = "⚠️ <b>Ошибки доставки</b>"
    else:
        leads = await list_leads(session)
        title = "📋 <b>Все лиды</b>"
    await _show_leads(callback, leads, title)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("leads:card:"))
async def lead_card(callback: CallbackQuery, session: AsyncSession) -> None:
    lead_id = int(callback.data.split(":")[-1])
    lead = await get_lead_by_id(session, lead_id)
    if not lead:
        await callback.answer("Лид не найден", show_alert=True)
        return
    await callback.message.edit_text(
        format_lead_card(lead),
        reply_markup=lead_card_kb(lead.id, lead.client_id, lead.form_id),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("leads:retry:"))
async def retry_delivery(callback: CallbackQuery, session: AsyncSession) -> None:
    lead_id = int(callback.data.split(":")[-1])
    lead = await deliver_lead(session, lead_id, bot=callback.bot)
    if not lead:
        await callback.answer("Лид не найден", show_alert=True)
        return
    await callback.message.edit_text(
        format_lead_card(lead),
        reply_markup=lead_card_kb(lead.id, lead.client_id, lead.form_id),
    )
    await callback.answer("Доставка повторена")


@router.callback_query(lambda c: c.data and c.data.startswith("leads:raw:"))
async def raw_lead(callback: CallbackQuery, session: AsyncSession) -> None:
    lead_id = int(callback.data.split(":")[-1])
    lead = await get_lead_by_id(session, lead_id)
    if not lead:
        await callback.answer("Лид не найден", show_alert=True)
        return
    raw = json.dumps(json.loads(lead.raw_data_json or "{}"), ensure_ascii=False, indent=2)
    text = f"📄 <b>Raw data #{lead.id}</b>\n\n<pre>{raw[:3200]}</pre>"
    await callback.message.edit_text(text, reply_markup=lead_card_kb(lead.id, lead.client_id, lead.form_id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("leads:client:"))
async def leads_by_client(callback: CallbackQuery, session: AsyncSession) -> None:
    client_id = int(callback.data.split(":")[-1])
    leads = list((await session.execute(select(Lead).where(Lead.client_id == client_id).order_by(Lead.created_at.desc()).limit(20))).scalars().all())
    await _show_leads(callback, leads, "📥 <b>Лиды клиента</b>")
    await callback.answer()


@router.callback_query(lambda c: c.data and (c.data.startswith("leads:form:") or c.data == "leads:by_form" or c.data == "leads:by_client"))
async def leads_stub(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.data and callback.data.startswith("leads:form:"):
        form_id = int(callback.data.split(":")[-1])
        leads = list((await session.execute(select(Lead).where(Lead.form_id == form_id).order_by(Lead.created_at.desc()).limit(20))).scalars().all())
        await _show_leads(callback, leads, "📋 <b>Лиды FB формы</b>")
    else:
        await callback.message.edit_text("Выбери клиента или форму из соответствующего раздела.", reply_markup=leads_menu_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "leads:export")
async def export_info(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📤 <b>Экспорт</b>\n\nCSV/XLSX экспорт подключается через сервис export_service. "
        "Для быстрой проверки используй базу или добавь отдельную команду выгрузки.",
        reply_markup=back_home_kb(),
    )
    await callback.answer()
