import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from config import PAGE_SIZE
from keyboards.admin_kb import (
    ClientCb, CancelCb, ConfirmCb, MenuCb,
    clients_list_kb, client_view_kb, cancel_kb, skip_cancel_kb,
    confirm_delete_kb, main_menu_kb,
)
from services.client_service import (
    get_clients_paginated, get_client_by_id, create_client,
    update_client_field, toggle_client_status, delete_client, search_clients,
)
from states.admin_states import CreateClientFSM, EditClientFSM
from utils.formatters import fmt_client
from utils.pagination import paginate

logger = logging.getLogger(__name__)
router = Router()


# ── List ──────────────────────────────────────────────────────────────────────

@router.callback_query(ClientCb.filter(F.action == "list"))
async def clients_list(
    callback: CallbackQuery, callback_data: ClientCb, session: AsyncSession
) -> None:
    page = callback_data.page
    items, total = await get_clients_paginated(session, page, PAGE_SIZE)
    pr = paginate(items, total, page, PAGE_SIZE)
    text = f"👥 <b>Клиенты</b> (всего: {total})\n\nВыберите клиента:"
    if not items:
        text += "\n\n<i>Клиентов пока нет.</i>"
    await callback.message.edit_text(text, reply_markup=clients_list_kb(pr), parse_mode="HTML")
    await callback.answer()


# ── Pagination redirect ───────────────────────────────────────────────────────

from keyboards.admin_kb import PaginateCb

@router.callback_query(PaginateCb.filter(F.section == "clients"))
async def clients_paginate(
    callback: CallbackQuery, callback_data: PaginateCb, session: AsyncSession
) -> None:
    page = callback_data.page
    items, total = await get_clients_paginated(session, page, PAGE_SIZE)
    pr = paginate(items, total, page, PAGE_SIZE)
    text = f"👥 <b>Клиенты</b> (всего: {total})\n\nВыберите клиента:"
    await callback.message.edit_text(text, reply_markup=clients_list_kb(pr), parse_mode="HTML")
    await callback.answer()


# ── View ──────────────────────────────────────────────────────────────────────

@router.callback_query(ClientCb.filter(F.action == "view"))
async def client_view(
    callback: CallbackQuery, callback_data: ClientCb, session: AsyncSession
) -> None:
    client = await get_client_by_id(session, callback_data.id)
    if not client:
        await callback.answer("Клиент не найден", show_alert=True)
        return
    text = fmt_client(client)
    await callback.message.edit_text(
        text, reply_markup=client_view_kb(client, callback_data.page), parse_mode="HTML"
    )
    await callback.answer()


# ── Create: start ─────────────────────────────────────────────────────────────

@router.callback_query(ClientCb.filter(F.action == "new"))
async def create_client_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreateClientFSM.waiting_name)
    await callback.message.edit_text(
        "➕ <b>Создание клиента</b>\n\n"
        "Шаг 1/3: Введите <b>имя клиента</b>:",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateClientFSM.waiting_name)
async def create_client_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip() if message.text else ""
    if len(name) < 2:
        await message.answer("❗ Имя слишком короткое (минимум 2 символа). Попробуйте снова:", reply_markup=cancel_kb())
        return
    await state.update_data(name=name)
    await state.set_state(CreateClientFSM.waiting_username)
    await message.answer(
        "Шаг 2/3: Введите <b>Telegram username</b> (без @) или нажмите «Пропустить»:",
        reply_markup=skip_cancel_kb(),
        parse_mode="HTML",
    )


@router.message(CreateClientFSM.waiting_username)
async def create_client_username(message: Message, state: FSMContext) -> None:
    username = (message.text or "").strip().lstrip("@") or None
    await state.update_data(telegram_username=username)
    await state.set_state(CreateClientFSM.waiting_notes)
    await message.answer(
        "Шаг 3/3: Добавьте <b>заметки</b> о клиенте или нажмите «Пропустить»:",
        reply_markup=skip_cancel_kb(),
        parse_mode="HTML",
    )


@router.message(CreateClientFSM.waiting_notes)
async def create_client_notes(message: Message, state: FSMContext, session: AsyncSession) -> None:
    notes = (message.text or "").strip() or None
    data = await state.get_data()
    client = await create_client(
        session,
        name=data["name"],
        telegram_username=data.get("telegram_username"),
        notes=notes,
    )
    await state.clear()
    text = f"✅ Клиент <b>{client.name}</b> создан!\n\n{fmt_client(client)}"
    await message.answer(text, reply_markup=client_view_kb(client), parse_mode="HTML")


# ── Edit handlers ─────────────────────────────────────────────────────────────

_FIELD_LABELS = {
    "edit_name": ("name", "имя"),
    "edit_username": ("telegram_username", "Telegram username (без @)"),
    "edit_notes": ("notes", "заметки"),
}


@router.callback_query(ClientCb.filter(F.action.in_({"edit_name", "edit_username", "edit_notes"})))
async def client_edit_start(
    callback: CallbackQuery, callback_data: ClientCb, state: FSMContext
) -> None:
    field, label = _FIELD_LABELS[callback_data.action]
    await state.set_state(EditClientFSM.waiting_value)
    await state.update_data(client_id=callback_data.id, field=field, page=callback_data.page)
    await callback.message.edit_text(
        f"✏️ Введите новое <b>{label}</b>:",
        reply_markup=skip_cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(EditClientFSM.waiting_value)
async def client_edit_value(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    value = (message.text or "").strip()
    client = await update_client_field(session, data["client_id"], data["field"], value)
    await state.clear()
    if not client:
        await message.answer("❗ Клиент не найден.", reply_markup=main_menu_kb())
        return
    await message.answer(
        f"✅ Изменено.\n\n{fmt_client(client)}",
        reply_markup=client_view_kb(client, data.get("page", 0)),
        parse_mode="HTML",
    )


# ── Toggle status ─────────────────────────────────────────────────────────────

@router.callback_query(ClientCb.filter(F.action == "toggle"))
async def client_toggle(
    callback: CallbackQuery, callback_data: ClientCb, session: AsyncSession
) -> None:
    client = await toggle_client_status(session, callback_data.id)
    if not client:
        await callback.answer("Клиент не найден", show_alert=True)
        return
    status_text = "включён ✅" if client.status == "active" else "выключен ⏸"
    await callback.answer(f"Статус изменён: {status_text}", show_alert=True)
    await callback.message.edit_text(
        fmt_client(client),
        reply_markup=client_view_kb(client, callback_data.page),
        parse_mode="HTML",
    )


# ── Delete ────────────────────────────────────────────────────────────────────

@router.callback_query(ClientCb.filter(F.action == "del"))
async def client_delete_confirm(
    callback: CallbackQuery, callback_data: ClientCb, session: AsyncSession
) -> None:
    client = await get_client_by_id(session, callback_data.id)
    if not client:
        await callback.answer("Клиент не найден", show_alert=True)
        return
    await callback.message.edit_text(
        f"🗑 Удалить клиента <b>{client.name}</b>?\n\n"
        f"⚠️ Вместе с клиентом удалятся все его офферы и лидформы!",
        reply_markup=confirm_delete_kb(f"client_{callback_data.id}_{callback_data.page}"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ConfirmCb.filter(F.action == "yes"))
async def handle_confirm_yes(
    callback: CallbackQuery, callback_data: ConfirmCb, session: AsyncSession
) -> None:
    target = callback_data.target
    if target.startswith("client_"):
        parts = target.split("_")
        client_id = int(parts[1])
        page = int(parts[2]) if len(parts) > 2 else 0
        client = await get_client_by_id(session, client_id)
        name = client.name if client else "?"
        await delete_client(session, client_id)
        await callback.answer(f"✅ Клиент «{name}» удалён.", show_alert=True)
        # Redirect to list
        items, total = await get_clients_paginated(session, max(0, page - 1), PAGE_SIZE)
        pr = paginate(items, total, max(0, page - 1), PAGE_SIZE)
        await callback.message.edit_text(
            f"👥 <b>Клиенты</b> (всего: {total})",
            reply_markup=clients_list_kb(pr),
            parse_mode="HTML",
        )
    else:
        await callback.answer("Удалено.", show_alert=True)
        await callback.message.edit_text("✅ Готово.", reply_markup=main_menu_kb())


@router.callback_query(ConfirmCb.filter(F.action == "no"))
async def handle_confirm_no(callback: CallbackQuery) -> None:
    await callback.answer("Отменено.")
    await callback.message.edit_text(
        "❌ Действие отменено.", reply_markup=main_menu_kb(), parse_mode="HTML"
    )


# ── Search ────────────────────────────────────────────────────────────────────

@router.callback_query(ClientCb.filter(F.action == "search"))
async def client_search_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreateClientFSM.confirming)
    await state.update_data(mode="search")
    await callback.message.edit_text(
        "🔍 Введите имя или username клиента для поиска:",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateClientFSM.confirming)
async def client_search_query(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    if data.get("mode") != "search":
        await state.clear()
        return
    query = (message.text or "").strip()
    if not query:
        await message.answer("❗ Введите строку поиска:", reply_markup=cancel_kb())
        return
    items, total = await search_clients(session, query)
    await state.clear()
    if not items:
        from keyboards.admin_kb import clients_section_kb
        await message.answer(f"Ничего не найдено по запросу «{query}».", reply_markup=clients_section_kb(), parse_mode="HTML")
        return
    from utils.pagination import paginate
    pr = paginate(items, total, 0, PAGE_SIZE)
    from keyboards.admin_kb import clients_list_kb
    await message.answer(
        f"🔍 Результаты поиска «{query}» ({total}):",
        reply_markup=clients_list_kb(pr),
        parse_mode="HTML",
    )


# ── Skip / Cancel handlers shared across FSMs ─────────────────────────────────

@router.callback_query(CancelCb.filter(F.action == "back"))
async def fsm_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "❌ Отменено.", reply_markup=main_menu_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(CancelCb.filter(F.action == "skip"))
async def fsm_skip(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    # Lazy imports to avoid circular dependencies
    from states.admin_states import (
        CreateOfferFSM, EditOfferFSM,
        CreateFormFSM, EditFormFSM,
        CreateRefFSM,
    )

    current = await state.get_state()
    if not current:
        await callback.answer()
        return

    # ── Client wizard ─────────────────────────────────────────────────────────
    if current == CreateClientFSM.waiting_username.state:
        await state.update_data(telegram_username=None)
        await state.set_state(CreateClientFSM.waiting_notes)
        await callback.message.edit_text(
            "Шаг 3/3: Добавьте <b>заметки</b> о клиенте или нажмите «Пропустить»:",
            reply_markup=skip_cancel_kb(),
            parse_mode="HTML",
        )
    elif current == CreateClientFSM.waiting_notes.state:
        data = await state.get_data()
        client = await create_client(
            session,
            name=data["name"],
            telegram_username=data.get("telegram_username"),
            notes=None,
        )
        await state.clear()
        await callback.message.edit_text(
            f"✅ Клиент <b>{client.name}</b> создан!\n\n{fmt_client(client)}",
            reply_markup=client_view_kb(client),
            parse_mode="HTML",
        )
    elif current == EditClientFSM.waiting_value.state:
        data = await state.get_data()
        client = await update_client_field(session, data["client_id"], data["field"], "")
        await state.clear()
        if client:
            await callback.message.edit_text(
                fmt_client(client), reply_markup=client_view_kb(client), parse_mode="HTML"
            )
        else:
            await callback.message.edit_text("✅ Готово.", reply_markup=main_menu_kb())

    # ── Offer wizard ──────────────────────────────────────────────────────────
    elif current == CreateOfferFSM.waiting_description.state:
        await state.update_data(description=None)
        await state.set_state(CreateOfferFSM.waiting_geo)
        await callback.message.edit_text(
            "Шаг 4/5: Введите <b>GEO</b> (напр. UA, RU, KZ или нажмите «Пропустить»):",
            reply_markup=skip_cancel_kb(),
            parse_mode="HTML",
        )
    elif current == CreateOfferFSM.waiting_geo.state:
        await state.update_data(geo=None)
        await state.set_state(CreateOfferFSM.waiting_language)
        await callback.message.edit_text(
            "Шаг 5/5: Введите <b>язык</b> оффера (напр. ru, uk или нажмите «Пропустить»):",
            reply_markup=skip_cancel_kb(),
            parse_mode="HTML",
        )
    elif current == CreateOfferFSM.waiting_language.state:
        from services.offer_service import create_offer as _co
        from utils.formatters import fmt_offer
        from keyboards.admin_kb import offer_view_kb
        data = await state.get_data()
        offer = await _co(
            session,
            client_id=data["client_id"],
            name=data["name"],
            description=data.get("description"),
            geo=data.get("geo"),
            language=None,
        )
        await state.clear()
        await callback.message.edit_text(
            f"✅ Оффер <b>{offer.name}</b> создан!\n\n{fmt_offer(offer)}",
            reply_markup=offer_view_kb(offer),
            parse_mode="HTML",
        )
    elif current == EditOfferFSM.waiting_value.state:
        from services.offer_service import update_offer_field as _uof
        from utils.formatters import fmt_offer
        from keyboards.admin_kb import offer_view_kb
        data = await state.get_data()
        offer = await _uof(session, data["offer_id"], data["field"], "")
        await state.clear()
        if offer:
            await callback.message.edit_text(
                fmt_offer(offer), reply_markup=offer_view_kb(offer), parse_mode="HTML"
            )
        else:
            await callback.message.edit_text("✅ Готово.", reply_markup=main_menu_kb())

    # ── Form wizard ───────────────────────────────────────────────────────────
    elif current == CreateFormFSM.waiting_language.state:
        await state.update_data(language="ru")
        await state.set_state(CreateFormFSM.waiting_welcome)
        await callback.message.edit_text(
            "Шаг 5/6: Введите <b>welcome-текст</b> (приветствие для пользователя):\n\n"
            "Или нажмите «Пропустить».",
            reply_markup=skip_cancel_kb(),
            parse_mode="HTML",
        )
    elif current == CreateFormFSM.waiting_welcome.state:
        await state.update_data(welcome_text=None)
        await state.set_state(CreateFormFSM.waiting_success)
        await callback.message.edit_text(
            "Шаг 6/6: Введите <b>success-текст</b> (показывается после отправки формы):\n\n"
            "Или нажмите «Пропустить».",
            reply_markup=skip_cancel_kb(),
            parse_mode="HTML",
        )
    elif current == CreateFormFSM.waiting_success.state:
        from services.form_service import create_form as _cf
        from utils.formatters import fmt_form
        from keyboards.admin_kb import form_view_kb
        data = await state.get_data()
        form = await _cf(
            session,
            client_id=data["client_id"],
            offer_id=data["offer_id"],
            name=data["name"],
            language=data.get("language", "ru"),
            welcome_text=data.get("welcome_text"),
            success_text=None,
        )
        await state.clear()
        await callback.message.edit_text(
            f"✅ Лидформа <b>{form.name}</b> создана!\n\n{fmt_form(form)}",
            reply_markup=form_view_kb(form),
            parse_mode="HTML",
        )
    elif current == EditFormFSM.waiting_value.state:
        from services.form_service import update_form_field as _uff
        from utils.formatters import fmt_form
        from keyboards.admin_kb import form_view_kb
        data = await state.get_data()
        form = await _uff(session, data["form_id"], data["field"], "")
        await state.clear()
        if form:
            await callback.message.edit_text(
                fmt_form(form), reply_markup=form_view_kb(form), parse_mode="HTML"
            )
        else:
            await callback.message.edit_text("✅ Готово.", reply_markup=main_menu_kb())

    # ── Ref wizard ────────────────────────────────────────────────────────────
    elif current == CreateRefFSM.waiting_notes.state:
        from services.referral_service import create_referral as _cr, build_start_link
        from utils.formatters import fmt_ref
        from keyboards.admin_kb import ref_view_kb
        from config import BOT_USERNAME
        data = await state.get_data()
        ref = await _cr(
            session,
            form_id=data["form_id"],
            name=data["name"],
            source_type=data["source_type"],
            notes=None,
        )
        await state.clear()
        link = build_start_link(ref.form_id, ref.code)
        text = (
            f"✅ Рефка <b>{ref.name}</b> создана!\n\n"
            f"{fmt_ref(ref, BOT_USERNAME)}\n\n"
            f"🔗 Ссылка для копирования:\n<code>{link}</code>"
        )
        await callback.message.edit_text(text, reply_markup=ref_view_kb(ref), parse_mode="HTML")

    else:
        await callback.answer()
        return
    await callback.answer()
