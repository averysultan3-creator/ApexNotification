from datetime import datetime
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.clients_kb import client_card_kb, clients_list_kb, clients_menu_kb
from app.bot.keyboards.leads_kb import leads_list_kb
from app.bot.states.client_states import AddClientFSM, AddTelegramIdFSM, SetSheetFSM
from app.services.client_service import (
    add_telegram_id, create_client, get_client_by_id, list_clients, set_google_sheet
)
from app.utils.formatters import load_json_list

router = Router(name="clients")


@router.callback_query(lambda c: c.data == "clients:menu")
async def clients_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    clients = await list_clients(session)
    await callback.message.edit_text(
        f"👥 <b>Клиенты</b>\n\nВсего: {len(clients)}",
        reply_markup=clients_menu_kb(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "clients:add")
async def clients_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddClientFSM.name)
    await callback.message.edit_text("👥 <b>Добавление клиента</b>\n\nВведи название:")
    await callback.answer()


@router.message(AddClientFSM.name)
async def clients_add_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    client = await create_client(session, name=message.text.strip())
    await state.clear()
    await message.answer(
        f"✅ Клиент <b>{client.name}</b> добавлен!\n"
        "Добавь Telegram ID и Google Sheet.",
        reply_markup=client_card_kb(client.id),
    )


@router.callback_query(lambda c: c.data == "clients:list")
async def clients_list(callback: CallbackQuery, session: AsyncSession) -> None:
    clients = await list_clients(session)
    if not clients:
        await callback.answer("Клиентов нет.", show_alert=True)
        return
    await callback.message.edit_text("👥 Клиенты:", reply_markup=clients_list_kb(clients))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("clients:card:"))
async def client_card(callback: CallbackQuery, session: AsyncSession) -> None:
    client_id = int(callback.data.split(":")[2])
    client = await get_client_by_id(session, client_id)
    if not client:
        await callback.answer("Клиент не найден.", show_alert=True)
        return
    tg_ids = load_json_list(client.telegram_ids_json)
    sheet_info = "подключён" if client.google_sheet_id else "не подключён"
    today = datetime.now().date().isoformat()
    today_count = sum(1 for l in client.leads if l.created_at.date().isoformat() == today)
    text = (
        f"👥 <b>{client.name}</b>\n\n"
        f"Telegram IDs:\n{chr(10).join(tg_ids) if tg_ids else '—'}\n\n"
        f"Google Sheet: {sheet_info}\n\n"
        f"Форм: {len(client.facebook_forms)}\n"
        f"Лидов сегодня: {today_count}"
    )
    await callback.message.edit_text(text, reply_markup=client_card_kb(client.id))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("clients:add_tid:"))
async def clients_add_tid_start(callback: CallbackQuery, state: FSMContext) -> None:
    client_id = int(callback.data.split(":")[2])
    await state.set_state(AddTelegramIdFSM.telegram_id)
    await state.update_data(client_id=client_id)
    await callback.message.edit_text("Введи Telegram ID (число, например 123456789):")
    await callback.answer()


@router.message(AddTelegramIdFSM.telegram_id)
async def clients_add_tid(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    tid = message.text.strip()
    if not tid.lstrip("-").isdigit():
        await message.answer("❌ Неверный формат. Введи числовой ID:")
        return
    client = await get_client_by_id(session, data["client_id"])
    if not client:
        await state.clear()
        await message.answer("Клиент не найден.")
        return
    await add_telegram_id(session, client, tid)
    await state.clear()
    await message.answer(
        f"✅ Telegram ID {tid} добавлен для <b>{client.name}</b>.",
        reply_markup=client_card_kb(client.id),
    )


@router.callback_query(lambda c: c.data.startswith("clients:set_sheet:"))
async def clients_set_sheet_start(callback: CallbackQuery, state: FSMContext) -> None:
    client_id = int(callback.data.split(":")[2])
    await state.set_state(SetSheetFSM.sheet_id)
    await state.update_data(client_id=client_id)
    await callback.message.edit_text(
        "📊 <b>Google Sheet</b>\n\n"
        "Введи ID таблицы\n"
        "(из URL: docs.google.com/spreadsheets/d/<b>ID</b>/edit):"
    )
    await callback.answer()


@router.message(SetSheetFSM.sheet_id)
async def clients_set_sheet_id(message: Message, state: FSMContext) -> None:
    await state.update_data(sheet_id=message.text.strip())
    await state.set_state(SetSheetFSM.sheet_name)
    await message.answer("Название листа (или /skip для Sheet1):")


@router.message(SetSheetFSM.sheet_name)
async def clients_set_sheet_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    client = await get_client_by_id(session, data["client_id"])
    if not client:
        await state.clear()
        await message.answer("Клиент не найден.")
        return
    sheet_name = message.text.strip() if message.text.strip() != "/skip" else "Sheet1"
    await set_google_sheet(session, client, data["sheet_id"], sheet_name)
    await state.clear()
    await message.answer(
        f"✅ Google Sheet подключён для <b>{client.name}</b>.\n"
        f"Лист: {sheet_name}",
        reply_markup=client_card_kb(client.id),
    )


@router.callback_query(lambda c: c.data.startswith("clients:leads:"))
async def client_leads(callback: CallbackQuery, session: AsyncSession) -> None:
    client_id = int(callback.data.split(":")[2])
    client = await get_client_by_id(session, client_id)
    if not client:
        await callback.answer("Клиент не найден.", show_alert=True)
        return
    leads = sorted(client.leads, key=lambda l: l.created_at, reverse=True)[:20]
    if not leads:
        await callback.answer("Лидов нет.", show_alert=True)
        return
    await callback.message.edit_text(
        f"📥 Лиды {client.name} (последние {len(leads)}):",
        reply_markup=leads_list_kb(leads, back_cb=f"clients:card:{client_id}"),
    )
    await callback.answer()
