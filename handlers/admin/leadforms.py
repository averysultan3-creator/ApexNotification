import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from config import PAGE_SIZE
from keyboards.admin_kb import (
    FormCb, FormEditCb, CancelCb, PaginateCb, ConfirmCb,
    SelectClientCb, SelectOfferCb, MenuCb,
    forms_list_kb, form_view_kb, cancel_kb, skip_cancel_kb,
    confirm_delete_kb, main_menu_kb, select_client_kb, select_offer_kb,
)
from services.client_service import get_clients_paginated
from services.offer_service import get_offers_by_client
from services.form_service import (
    get_forms_paginated, get_form_by_id, create_form,
    update_form_field, toggle_form_status, delete_form,
)
from states.admin_states import CreateFormFSM, EditFormFSM
from utils.formatters import fmt_form
from utils.pagination import paginate

logger = logging.getLogger(__name__)
router = Router()


# ── List ──────────────────────────────────────────────────────────────────────

@router.callback_query(FormCb.filter(F.action == "list"))
async def forms_list(
    callback: CallbackQuery, callback_data: FormCb, session: AsyncSession
) -> None:
    page = callback_data.page
    items, total = await get_forms_paginated(session, page, PAGE_SIZE)
    pr = paginate(items, total, page, PAGE_SIZE)
    text = f"📝 <b>Лидформы</b> (всего: {total})\n\nВыберите форму:"
    if not items:
        text += "\n\n<i>Форм пока нет.</i>"
    await callback.message.edit_text(text, reply_markup=forms_list_kb(pr), parse_mode="HTML")
    await callback.answer()


@router.callback_query(PaginateCb.filter(F.section == "forms"))
async def forms_paginate(
    callback: CallbackQuery, callback_data: PaginateCb, session: AsyncSession
) -> None:
    items, total = await get_forms_paginated(session, callback_data.page, PAGE_SIZE)
    pr = paginate(items, total, callback_data.page, PAGE_SIZE)
    await callback.message.edit_text(
        f"📝 <b>Лидформы</b> (всего: {total})",
        reply_markup=forms_list_kb(pr),
        parse_mode="HTML",
    )
    await callback.answer()


# ── View ──────────────────────────────────────────────────────────────────────

@router.callback_query(FormCb.filter(F.action == "view"))
async def form_view(
    callback: CallbackQuery, callback_data: FormCb, session: AsyncSession
) -> None:
    form = await get_form_by_id(session, callback_data.id)
    if not form:
        await callback.answer("Форма не найдена", show_alert=True)
        return
    await callback.message.edit_text(
        fmt_form(form), reply_markup=form_view_kb(form, callback_data.page), parse_mode="HTML"
    )
    await callback.answer()


# ── Create: wizard ────────────────────────────────────────────────────────────

@router.callback_query(FormCb.filter(F.action == "new"))
async def create_form_start(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    clients, total = await get_clients_paginated(session, 0, 50)
    if not clients:
        await callback.answer("Сначала создайте клиента.", show_alert=True)
        return
    await state.set_state(CreateFormFSM.select_client)
    await callback.message.edit_text(
        "➕ <b>Создание лидформы</b>\n\nШаг 1/6: Выберите <b>клиента</b>:",
        reply_markup=select_client_kb(clients),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(SelectClientCb.filter(), CreateFormFSM.select_client)
async def create_form_client(
    callback: CallbackQuery, callback_data: SelectClientCb, state: FSMContext, session: AsyncSession
) -> None:
    client_id = callback_data.client_id
    offers = await get_offers_by_client(session, client_id)
    if not offers:
        await callback.answer("У этого клиента нет активных офферов. Сначала создайте оффер.", show_alert=True)
        return
    await state.update_data(client_id=client_id)
    await state.set_state(CreateFormFSM.select_offer)
    await callback.message.edit_text(
        "Шаг 2/6: Выберите <b>оффер</b>:",
        reply_markup=select_offer_kb(offers),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(SelectOfferCb.filter(), CreateFormFSM.select_offer)
async def create_form_offer(
    callback: CallbackQuery, callback_data: SelectOfferCb, state: FSMContext
) -> None:
    await state.update_data(offer_id=callback_data.offer_id)
    await state.set_state(CreateFormFSM.waiting_name)
    await callback.message.edit_text(
        "Шаг 3/6: Введите <b>название формы</b>:",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateFormFSM.waiting_name)
async def create_form_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("❗ Слишком короткое название.", reply_markup=cancel_kb())
        return
    await state.update_data(name=name)
    await state.set_state(CreateFormFSM.waiting_language)
    await message.answer(
        "Шаг 4/6: Введите <b>язык формы</b> (ru, uk, en … или нажмите «Пропустить» для ru):",
        reply_markup=skip_cancel_kb(),
        parse_mode="HTML",
    )


@router.message(CreateFormFSM.waiting_language)
async def create_form_language(message: Message, state: FSMContext) -> None:
    lang = (message.text or "").strip().lower() or "ru"
    await state.update_data(language=lang)
    await state.set_state(CreateFormFSM.waiting_welcome)
    await message.answer(
        "Шаг 5/6: Введите <b>welcome-текст</b> (приветствие для пользователя):\n\n"
        "Или нажмите «Пропустить».",
        reply_markup=skip_cancel_kb(),
        parse_mode="HTML",
    )


@router.message(CreateFormFSM.waiting_welcome)
async def create_form_welcome(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip() or None
    await state.update_data(welcome_text=text)
    await state.set_state(CreateFormFSM.waiting_success)
    await message.answer(
        "Шаг 6/6: Введите <b>success-текст</b> (показывается после отправки формы):\n\n"
        "Или нажмите «Пропустить».",
        reply_markup=skip_cancel_kb(),
        parse_mode="HTML",
    )


@router.message(CreateFormFSM.waiting_success)
async def create_form_success(message: Message, state: FSMContext, session: AsyncSession) -> None:
    success_text = (message.text or "").strip() or None
    data = await state.get_data()
    form = await create_form(
        session,
        client_id=data["client_id"],
        offer_id=data["offer_id"],
        name=data["name"],
        language=data.get("language", "ru"),
        welcome_text=data.get("welcome_text"),
        success_text=success_text,
    )
    await state.clear()
    await message.answer(
        f"✅ Лидформа <b>{form.name}</b> создана!\n\n{fmt_form(form)}",
        reply_markup=form_view_kb(form),
        parse_mode="HTML",
    )


# ── Edit ──────────────────────────────────────────────────────────────────────

_FIELD_LABELS = {
    "name": "название",
    "language": "язык",
    "welcome_text": "welcome-текст",
    "success_text": "success-текст",
}


@router.callback_query(FormEditCb.filter())
async def form_edit_start(
    callback: CallbackQuery, callback_data: FormEditCb, state: FSMContext
) -> None:
    field = callback_data.field
    label = _FIELD_LABELS.get(field, field)
    await state.set_state(EditFormFSM.waiting_value)
    await state.update_data(form_id=callback_data.id, field=field)
    await callback.message.edit_text(
        f"✏️ Введите новый <b>{label}</b>:",
        reply_markup=skip_cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(EditFormFSM.waiting_value)
async def form_edit_value(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    value = (message.text or "").strip()
    form = await update_form_field(session, data["form_id"], data["field"], value)
    await state.clear()
    if not form:
        await message.answer("❗ Форма не найдена.", reply_markup=main_menu_kb())
        return
    await message.answer(
        f"✅ Изменено.\n\n{fmt_form(form)}",
        reply_markup=form_view_kb(form),
        parse_mode="HTML",
    )


# ── Toggle ────────────────────────────────────────────────────────────────────

@router.callback_query(FormCb.filter(F.action == "toggle"))
async def form_toggle(
    callback: CallbackQuery, callback_data: FormCb, session: AsyncSession
) -> None:
    form = await toggle_form_status(session, callback_data.id)
    if not form:
        await callback.answer("Форма не найдена", show_alert=True)
        return
    label = "включена ✅" if form.status == "active" else "выключена ⏸"
    await callback.answer(f"Форма {label}", show_alert=True)
    await callback.message.edit_text(
        fmt_form(form), reply_markup=form_view_kb(form, callback_data.page), parse_mode="HTML"
    )


# ── Delete ────────────────────────────────────────────────────────────────────

@router.callback_query(FormCb.filter(F.action == "del"))
async def form_delete_confirm(
    callback: CallbackQuery, callback_data: FormCb, session: AsyncSession
) -> None:
    form = await get_form_by_id(session, callback_data.id)
    if not form:
        await callback.answer("Форма не найдена", show_alert=True)
        return
    await callback.message.edit_text(
        f"🗑 Удалить форму <b>{form.name}</b>?\n\n⚠️ Удалятся все вопросы, рефки и лиды формы!",
        reply_markup=confirm_delete_kb(f"form_{callback_data.id}_{callback_data.page}"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ConfirmCb.filter(F.target.startswith("form_")))
async def form_delete_do(
    callback: CallbackQuery, callback_data: ConfirmCb, session: AsyncSession
) -> None:
    if callback_data.action != "yes":
        await callback.answer("Отменено.")
        await callback.message.edit_text("❌ Отменено.", reply_markup=main_menu_kb())
        return
    parts = callback_data.target.split("_")
    form_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 0
    form = await get_form_by_id(session, form_id)
    name = form.name if form else "?"
    await delete_form(session, form_id)
    await callback.answer(f"✅ Форма «{name}» удалена.", show_alert=True)
    items, total = await get_forms_paginated(session, max(0, page - 1), PAGE_SIZE)
    pr = paginate(items, total, max(0, page - 1), PAGE_SIZE)
    await callback.message.edit_text(
        f"📝 <b>Лидформы</b> (всего: {total})",
        reply_markup=forms_list_kb(pr),
        parse_mode="HTML",
    )
