import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from config import PAGE_SIZE
from keyboards.admin_kb import (
    LeadCb, LeadStatusCb, LeadFilterCb, PaginateCb, MenuCb, FormCb,
    SelectClientCb, SelectOfferCb,
    leads_list_kb, lead_view_kb, lead_status_kb, lead_filter_kb,
    filter_status_kb, cancel_kb, main_menu_kb, leads_section_kb,
)
from services.lead_service import (
    get_leads_paginated, get_lead_by_id, update_lead_status, update_lead_notes,
)
from services.client_service import get_clients_paginated
from services.offer_service import get_offers_paginated, get_offer_by_id
from services.form_service import get_forms_paginated
from states.admin_states import LeadFilterFSM, LeadNoteFSM
from utils.formatters import fmt_lead
from utils.pagination import paginate
from utils.validators import validate_date

logger = logging.getLogger(__name__)
router = Router()

_FILTER_KEY = "leads_filter"


def _get_filter(data: dict) -> dict:
    return data.get(_FILTER_KEY, {})


# ── List ──────────────────────────────────────────────────────────────────────

@router.callback_query(LeadCb.filter(F.action == "list"))
async def leads_list(
    callback: CallbackQuery, callback_data: LeadCb, state: FSMContext, session: AsyncSession
) -> None:
    page = callback_data.page
    state_data = await state.get_data()
    filters = _get_filter(state_data)
    items, total = await get_leads_paginated(session, page, PAGE_SIZE, filters=filters or None)
    pr = paginate(items, total, page, PAGE_SIZE)
    has_filter = bool(filters)
    filter_text = " (с фильтром 🔍)" if has_filter else ""
    text = f"📥 <b>Лиды</b> (всего: {total}){filter_text}\n\nВыберите лид:"
    if not items:
        text += "\n\n<i>Лидов нет.</i>"
    await callback.message.edit_text(
        text, reply_markup=leads_list_kb(pr, has_filter), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(PaginateCb.filter(F.section == "leads"))
async def leads_paginate(
    callback: CallbackQuery, callback_data: PaginateCb, state: FSMContext, session: AsyncSession
) -> None:
    state_data = await state.get_data()
    filters = _get_filter(state_data)
    items, total = await get_leads_paginated(
        session, callback_data.page, PAGE_SIZE, filters=filters or None
    )
    pr = paginate(items, total, callback_data.page, PAGE_SIZE)
    await callback.message.edit_text(
        f"📥 <b>Лиды</b> (всего: {total})",
        reply_markup=leads_list_kb(pr, bool(filters)),
        parse_mode="HTML",
    )
    await callback.answer()


# ── View lead ─────────────────────────────────────────────────────────────────

@router.callback_query(LeadCb.filter(F.action == "view"))
async def lead_view(
    callback: CallbackQuery, callback_data: LeadCb, session: AsyncSession
) -> None:
    lead = await get_lead_by_id(session, callback_data.id)
    if not lead:
        await callback.answer("Лид не найден", show_alert=True)
        return
    await callback.message.edit_text(
        fmt_lead(lead), reply_markup=lead_view_kb(lead, callback_data.page), parse_mode="HTML"
    )
    await callback.answer()


# ── By form ───────────────────────────────────────────────────────────────────

@router.callback_query(LeadCb.filter(F.action == "by_form"))
async def leads_by_form(
    callback: CallbackQuery, callback_data: LeadCb, state: FSMContext, session: AsyncSession
) -> None:
    form_id = callback_data.id
    items, total = await get_leads_paginated(
        session, 0, PAGE_SIZE, filters={"form_id": form_id}
    )
    pr = paginate(items, total, 0, PAGE_SIZE)
    await callback.message.edit_text(
        f"📥 <b>Лиды формы</b> (всего: {total})",
        reply_markup=leads_list_kb(pr),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Change status ─────────────────────────────────────────────────────────────

@router.callback_query(LeadCb.filter(F.action == "change_status"))
async def lead_change_status_menu(
    callback: CallbackQuery, callback_data: LeadCb, session: AsyncSession
) -> None:
    lead = await get_lead_by_id(session, callback_data.id)
    if not lead:
        await callback.answer("Лид не найден", show_alert=True)
        return
    await callback.message.edit_text(
        f"Лид <b>#{lead.id}</b>: выберите новый статус:",
        reply_markup=lead_status_kb(lead.id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(LeadStatusCb.filter())
async def lead_set_status(
    callback: CallbackQuery, callback_data: LeadStatusCb, session: AsyncSession
) -> None:
    lead = await get_lead_by_id(session, callback_data.lead_id)
    if not lead:
        await callback.answer("Лид не найден", show_alert=True)
        return
    old_status = lead.status
    lead = await update_lead_status(session, callback_data.lead_id, callback_data.status)
    if not lead:
        await callback.answer("Лид не найден", show_alert=True)
        return
    # Track status change
    try:
        from services.tracking_service import track_lead_status_changed
        await track_lead_status_changed(
            session,
            lead_id=lead.id,
            old_status=old_status,
            new_status=callback_data.status,
            form_id=lead.form_id,
            client_id=lead.client_id,
            offer_id=lead.offer_id,
            referral_source_id=lead.referral_source_id,
        )
    except Exception as _te:
        logger.debug("Tracking lead status change failed (non-critical): %s", _te)
    await callback.answer(f"✅ Статус изменён: {callback_data.status}", show_alert=True)
    await callback.message.edit_text(
        fmt_lead(lead), reply_markup=lead_view_kb(lead), parse_mode="HTML"
    )


# ── Add note ──────────────────────────────────────────────────────────────────

@router.callback_query(LeadCb.filter(F.action == "add_note"))
async def lead_add_note_start(
    callback: CallbackQuery, callback_data: LeadCb, state: FSMContext
) -> None:
    await state.set_state(LeadNoteFSM.waiting_note)
    await state.update_data(note_lead_id=callback_data.id)
    await callback.message.edit_text(
        "📝 Введите заметку для этого лида:",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(LeadNoteFSM.waiting_note)
async def lead_save_note(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    notes = (message.text or "").strip()
    lead_id = data["note_lead_id"]
    lead = await update_lead_notes(session, lead_id, notes)
    await state.clear()
    if not lead:
        await message.answer("❗ Лид не найден.", reply_markup=main_menu_kb())
        return
    await message.answer(
        f"✅ Заметка сохранена.\n\n{fmt_lead(lead)}",
        reply_markup=lead_view_kb(lead),
        parse_mode="HTML",
    )


# ── Filter ────────────────────────────────────────────────────────────────────

@router.callback_query(LeadCb.filter(F.action == "filter"))
async def lead_filter_menu(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    current = _get_filter(data)
    await callback.message.edit_text(
        "🔍 <b>Фильтр лидов</b>\n\nНастройте фильтры:",
        reply_markup=lead_filter_kb(current),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(LeadCb.filter(F.action == "reset_filter"))
async def lead_reset_filter(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    data.pop(_FILTER_KEY, None)
    await state.set_data(data)
    await callback.answer("✅ Фильтр сброшен.")
    await callback.message.edit_text(
        "📥 <b>Лиды</b>\n\nФильтр сброшен.", reply_markup=leads_section_kb(), parse_mode="HTML"
    )


@router.callback_query(LeadFilterCb.filter(F.field == "status"))
async def lead_filter_status(callback: CallbackQuery, callback_data: LeadFilterCb, state: FSMContext) -> None:
    if not callback_data.val:
        # Show status picker
        await callback.message.edit_text(
            "Выберите статус:",
            reply_markup=filter_status_kb(),
            parse_mode="HTML",
        )
        await callback.answer()
    else:
        data = await state.get_data()
        current = _get_filter(data)
        current["status"] = callback_data.val
        await state.update_data(**{_FILTER_KEY: current})
        await callback.answer(f"✅ Статус: {callback_data.val}")
        await callback.message.edit_text(
            "🔍 <b>Фильтр</b>", reply_markup=lead_filter_kb(current), parse_mode="HTML"
        )


@router.callback_query(LeadFilterCb.filter(F.field == "client_id"))
async def lead_filter_client(
    callback: CallbackQuery, callback_data: LeadFilterCb, state: FSMContext, session: AsyncSession
) -> None:
    from keyboards.admin_kb import select_client_kb
    clients, _ = await get_clients_paginated(session, 0, 50)
    await callback.message.edit_text(
        "Выберите клиента для фильтра:",
        reply_markup=select_client_kb(clients),
        parse_mode="HTML",
    )
    await state.set_state(LeadFilterFSM.waiting_client)
    await callback.answer()


@router.callback_query(LeadFilterCb.filter(F.field == "offer_id"))
async def lead_filter_offer(
    callback: CallbackQuery, callback_data: LeadFilterCb, state: FSMContext, session: AsyncSession
) -> None:
    from keyboards.admin_kb import select_offer_kb
    offers, _ = await get_offers_paginated(session, 0, 50)
    await callback.message.edit_text(
        "Выберите оффер для фильтра:",
        reply_markup=select_offer_kb(offers),
        parse_mode="HTML",
    )
    await state.set_state(LeadFilterFSM.waiting_offer)
    await callback.answer()


@router.callback_query(LeadFilterCb.filter(F.field == "form_id"))
async def lead_filter_form(
    callback: CallbackQuery, callback_data: LeadFilterCb, state: FSMContext, session: AsyncSession
) -> None:
    if callback_data.val:
        # A form was selected
        try:
            form_id = int(callback_data.val)
        except (ValueError, TypeError):
            await callback.answer("❗ Неверный ID формы.")
            return
        data = await state.get_data()
        current = _get_filter(data)
        current["form_id"] = form_id
        # Fetch form name for display in filter button
        from services.form_service import get_form_by_id as _get_form
        form = await _get_form(session, form_id)
        current["form_name"] = form.name if form else str(form_id)
        await state.update_data(**{_FILTER_KEY: current})
        await callback.answer("✅ Форма выбрана.")
        await callback.message.edit_text(
            "🔍 <b>Фильтр</b>", reply_markup=lead_filter_kb(current), parse_mode="HTML"
        )
        return

    forms, _ = await get_forms_paginated(session, 0, 50)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from keyboards.admin_kb import LeadFilterCb as LFC
    b = InlineKeyboardBuilder()
    for f in forms:
        b.button(text=f.name, callback_data=LFC(field="form_id", val=str(f.id)))
    b.button(text="◀️ Назад", callback_data=MenuCb(section="leads"))
    b.adjust(1)
    await callback.message.edit_text(
        "Выберите форму для фильтра:",
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


# SelectClientCb / SelectOfferCb in leads filter context

@router.callback_query(SelectClientCb.filter(), LeadFilterFSM.waiting_client)
async def lead_filter_pick_client(
    callback: CallbackQuery, callback_data: SelectClientCb, state: FSMContext, session: AsyncSession
) -> None:
    from services.client_service import get_client_by_id as _get_client
    client = await _get_client(session, callback_data.client_id)
    data = await state.get_data()
    current = _get_filter(data)
    current["client_id"] = callback_data.client_id
    current["client_name"] = client.name if client else str(callback_data.client_id)
    await state.update_data(**{_FILTER_KEY: current})
    await state.set_state(None)
    await callback.answer(f"✅ Клиент: {current['client_name']}")
    await callback.message.edit_text(
        "🔍 <b>Фильтр</b>", reply_markup=lead_filter_kb(current), parse_mode="HTML"
    )


@router.callback_query(SelectOfferCb.filter(), LeadFilterFSM.waiting_offer)
async def lead_filter_pick_offer(
    callback: CallbackQuery, callback_data: SelectOfferCb, state: FSMContext, session: AsyncSession
) -> None:
    offer = await get_offer_by_id(session, callback_data.offer_id)
    data = await state.get_data()
    current = _get_filter(data)
    current["offer_id"] = callback_data.offer_id
    current["offer_name"] = offer.name if offer else str(callback_data.offer_id)
    await state.update_data(**{_FILTER_KEY: current})
    await state.set_state(None)
    await callback.answer(f"✅ Оффер: {current['offer_name']}")
    await callback.message.edit_text(
        "🔍 <b>Фильтр</b>", reply_markup=lead_filter_kb(current), parse_mode="HTML"
    )


@router.callback_query(LeadFilterCb.filter(F.field == "date_from"))
async def lead_filter_date_from_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(LeadFilterFSM.waiting_date_from)
    await callback.message.edit_text(
        "📅 Введите дату <b>от</b> (формат: дд.мм.гггг):",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(LeadFilterFSM.waiting_date_from)
async def lead_filter_date_from(message: Message, state: FSMContext) -> None:
    date_val = validate_date((message.text or "").strip())
    if not date_val:
        await message.answer("❗ Неверный формат даты. Введите дд.мм.гггг:", reply_markup=cancel_kb())
        return
    data = await state.get_data()
    current_filter = _get_filter(data)
    current_filter["date_from"] = date_val
    await state.update_data(**{_FILTER_KEY: current_filter})
    await state.set_state(None)
    await message.answer(
        f"✅ Фильтр «Дата от» установлен: {date_val}",
        reply_markup=lead_filter_kb(current_filter),
        parse_mode="HTML",
    )


@router.callback_query(LeadFilterCb.filter(F.field == "date_to"))
async def lead_filter_date_to_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(LeadFilterFSM.waiting_date_to)
    await callback.message.edit_text(
        "📅 Введите дату <b>до</b> (формат: дд.мм.гггг):",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(LeadFilterFSM.waiting_date_to)
async def lead_filter_date_to(message: Message, state: FSMContext) -> None:
    date_val = validate_date((message.text or "").strip())
    if not date_val:
        await message.answer("❗ Неверный формат. Введите дд.мм.гггг:", reply_markup=cancel_kb())
        return
    data = await state.get_data()
    current = _get_filter(data)
    current["date_to"] = date_val
    await state.update_data(**{_FILTER_KEY: current})
    await state.set_state(None)
    await message.answer(
        f"✅ Фильтр «Дата до» установлен: {date_val}",
        reply_markup=lead_filter_kb(current),
        parse_mode="HTML",
    )
