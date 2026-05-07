import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from config import PAGE_SIZE
from keyboards.admin_kb import (
    OfferCb, CancelCb, PaginateCb, SelectClientCb, MenuCb,
    offers_list_kb, offer_view_kb, cancel_kb, skip_cancel_kb,
    confirm_delete_kb, main_menu_kb, select_client_kb,
)
from services.client_service import get_clients_paginated
from services.offer_service import (
    get_offers_paginated, get_offer_by_id, create_offer,
    update_offer_field, toggle_offer_status, delete_offer,
)
from states.admin_states import CreateOfferFSM, EditOfferFSM
from utils.formatters import fmt_offer
from utils.pagination import paginate

logger = logging.getLogger(__name__)
router = Router()


# ── List ──────────────────────────────────────────────────────────────────────

@router.callback_query(OfferCb.filter(F.action == "list"))
async def offers_list(
    callback: CallbackQuery, callback_data: OfferCb, session: AsyncSession
) -> None:
    page = callback_data.page
    client_id = callback_data.client_id or None
    items, total = await get_offers_paginated(session, page, PAGE_SIZE, client_id=client_id)
    pr = paginate(items, total, page, PAGE_SIZE)
    text = f"📦 <b>Офферы</b> (всего: {total})\n\nВыберите оффер:"
    if not items:
        text += "\n\n<i>Офферов пока нет.</i>"
    await callback.message.edit_text(
        text, reply_markup=offers_list_kb(pr, client_id or 0), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(PaginateCb.filter(F.section == "offers"))
async def offers_paginate(
    callback: CallbackQuery, callback_data: PaginateCb, session: AsyncSession
) -> None:
    page = callback_data.page
    client_id = callback_data.extra or None
    items, total = await get_offers_paginated(session, page, PAGE_SIZE, client_id=client_id)
    pr = paginate(items, total, page, PAGE_SIZE)
    await callback.message.edit_text(
        f"📦 <b>Офферы</b> (всего: {total})",
        reply_markup=offers_list_kb(pr, client_id or 0),
        parse_mode="HTML",
    )
    await callback.answer()


# ── View ──────────────────────────────────────────────────────────────────────

@router.callback_query(OfferCb.filter(F.action == "view"))
async def offer_view(
    callback: CallbackQuery, callback_data: OfferCb, session: AsyncSession
) -> None:
    offer = await get_offer_by_id(session, callback_data.id)
    if not offer:
        await callback.answer("Оффер не найден", show_alert=True)
        return
    await callback.message.edit_text(
        fmt_offer(offer), reply_markup=offer_view_kb(offer, callback_data.page), parse_mode="HTML"
    )
    await callback.answer()


# ── Create: wizard ────────────────────────────────────────────────────────────

@router.callback_query(OfferCb.filter(F.action == "new"))
async def create_offer_start(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    clients, total = await get_clients_paginated(session, 0, 50)
    if not clients:
        await callback.answer("Сначала создайте хотя бы одного клиента.", show_alert=True)
        return
    await state.set_state(CreateOfferFSM.select_client)
    await callback.message.edit_text(
        "➕ <b>Создание оффера</b>\n\nШаг 1/5: Выберите <b>клиента</b>:",
        reply_markup=select_client_kb(clients),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(SelectClientCb.filter(), CreateOfferFSM.select_client)
async def create_offer_client_selected(
    callback: CallbackQuery, callback_data: SelectClientCb, state: FSMContext
) -> None:
    await state.update_data(client_id=callback_data.client_id)
    await state.set_state(CreateOfferFSM.waiting_name)
    await callback.message.edit_text(
        "Шаг 2/5: Введите <b>название оффера</b>:",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateOfferFSM.waiting_name)
async def create_offer_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("❗ Название слишком короткое. Попробуйте снова:", reply_markup=cancel_kb())
        return
    await state.update_data(name=name)
    await state.set_state(CreateOfferFSM.waiting_description)
    await message.answer(
        "Шаг 3/5: Введите <b>описание</b> оффера (или нажмите «Пропустить»):",
        reply_markup=skip_cancel_kb(),
        parse_mode="HTML",
    )


@router.message(CreateOfferFSM.waiting_description)
async def create_offer_description(message: Message, state: FSMContext) -> None:
    desc = (message.text or "").strip() or None
    await state.update_data(description=desc)
    await state.set_state(CreateOfferFSM.waiting_geo)
    await message.answer(
        "Шаг 4/5: Введите <b>GEO</b> (напр. UA, RU, KZ или нажмите «Пропустить»):",
        reply_markup=skip_cancel_kb(),
        parse_mode="HTML",
    )


@router.message(CreateOfferFSM.waiting_geo)
async def create_offer_geo(message: Message, state: FSMContext) -> None:
    geo = (message.text or "").strip() or None
    await state.update_data(geo=geo)
    await state.set_state(CreateOfferFSM.waiting_language)
    await message.answer(
        "Шаг 5/5: Введите <b>язык</b> оффера (напр. ru, uk или нажмите «Пропустить»):",
        reply_markup=skip_cancel_kb(),
        parse_mode="HTML",
    )


@router.message(CreateOfferFSM.waiting_language)
async def create_offer_language(message: Message, state: FSMContext, session: AsyncSession) -> None:
    lang = (message.text or "").strip() or None
    data = await state.get_data()
    offer = await create_offer(
        session,
        client_id=data["client_id"],
        name=data["name"],
        description=data.get("description"),
        geo=data.get("geo"),
        language=lang,
    )
    await state.clear()
    await message.answer(
        f"✅ Оффер <b>{offer.name}</b> создан!\n\n{fmt_offer(offer)}",
        reply_markup=offer_view_kb(offer),
        parse_mode="HTML",
    )


# ── Edit ──────────────────────────────────────────────────────────────────────

_FIELD_MAP = {
    "edit_name": ("name", "название"),
    "edit_desc": ("description", "описание"),
    "edit_geo": ("geo", "GEO"),
    "edit_lang": ("language", "язык"),
}


@router.callback_query(OfferCb.filter(F.action.in_({"edit_name", "edit_desc", "edit_geo", "edit_lang"})))
async def offer_edit_start(
    callback: CallbackQuery, callback_data: OfferCb, state: FSMContext
) -> None:
    field, label = _FIELD_MAP[callback_data.action]
    await state.set_state(EditOfferFSM.waiting_value)
    await state.update_data(offer_id=callback_data.id, field=field, page=callback_data.page)
    await callback.message.edit_text(
        f"✏️ Введите новое <b>{label}</b>:",
        reply_markup=skip_cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(EditOfferFSM.waiting_value)
async def offer_edit_value(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    value = (message.text or "").strip()
    offer = await update_offer_field(session, data["offer_id"], data["field"], value)
    await state.clear()
    if not offer:
        await message.answer("❗ Оффер не найден.", reply_markup=main_menu_kb())
        return
    await message.answer(
        f"✅ Изменено.\n\n{fmt_offer(offer)}",
        reply_markup=offer_view_kb(offer, data.get("page", 0)),
        parse_mode="HTML",
    )


# ── Toggle ────────────────────────────────────────────────────────────────────

@router.callback_query(OfferCb.filter(F.action == "toggle"))
async def offer_toggle(
    callback: CallbackQuery, callback_data: OfferCb, session: AsyncSession
) -> None:
    offer = await toggle_offer_status(session, callback_data.id)
    if not offer:
        await callback.answer("Оффер не найден", show_alert=True)
        return
    status_text = "включён ✅" if offer.status == "active" else "выключен ⏸"
    await callback.answer(f"Статус изменён: {status_text}", show_alert=True)
    await callback.message.edit_text(
        fmt_offer(offer), reply_markup=offer_view_kb(offer, callback_data.page), parse_mode="HTML"
    )


# ── Delete ────────────────────────────────────────────────────────────────────

@router.callback_query(OfferCb.filter(F.action == "del"))
async def offer_delete_confirm(
    callback: CallbackQuery, callback_data: OfferCb, session: AsyncSession
) -> None:
    offer = await get_offer_by_id(session, callback_data.id)
    if not offer:
        await callback.answer("Оффер не найден", show_alert=True)
        return
    await callback.message.edit_text(
        f"🗑 Удалить оффер <b>{offer.name}</b>?\n\n"
        "⚠️ Вместе с оффером удалятся все его лидформы!",
        reply_markup=confirm_delete_kb(f"offer_{callback_data.id}_{callback_data.page}"),
        parse_mode="HTML",
    )
    await callback.answer()


# ConfirmCb for offers is handled in clients.py (shared)
# We add offer handling here:
from keyboards.admin_kb import ConfirmCb  # noqa: E402


@router.callback_query(ConfirmCb.filter(F.target.startswith("offer_")))
async def offer_delete_do(
    callback: CallbackQuery, callback_data: ConfirmCb, session: AsyncSession
) -> None:
    if callback_data.action != "yes":
        await callback.answer("Отменено.")
        await callback.message.edit_text("❌ Отменено.", reply_markup=main_menu_kb())
        return
    parts = callback_data.target.split("_")
    offer_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 0
    offer = await get_offer_by_id(session, offer_id)
    name = offer.name if offer else "?"
    await delete_offer(session, offer_id)
    await callback.answer(f"✅ Оффер «{name}» удалён.", show_alert=True)
    items, total = await get_offers_paginated(session, max(0, page - 1), PAGE_SIZE)
    pr = paginate(items, total, max(0, page - 1), PAGE_SIZE)
    await callback.message.edit_text(
        f"📦 <b>Офферы</b> (всего: {total})",
        reply_markup=offers_list_kb(pr),
        parse_mode="HTML",
    )
