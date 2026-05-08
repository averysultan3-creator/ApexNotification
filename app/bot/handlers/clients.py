from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.clients_kb import client_card_kb, clients_menu_kb
from app.bot.states.client_states import ClientAddEmail, ClientAddTelegram, ClientCreate
from app.services.client_service import (
    add_client_email,
    add_client_telegram_id,
    create_client,
    get_client_by_id,
    get_client_counts,
    list_clients,
)
from app.utils.formatters import format_client_card
from app.utils.validators import is_valid_email

router = Router(name="clients")


@router.callback_query(lambda c: c.data == "clients:menu")
async def clients_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    clients = await list_clients(session)
    active = sum(1 for client in clients if client.status == "active")
    await callback.message.edit_text(
        f"👥 <b>Клиенты</b>\n\nВсего: {len(clients)}\nАктивных: {active}",
        reply_markup=clients_menu_kb(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "clients:add")
async def add_client_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ClientCreate.name)
    await callback.message.edit_text("Шаг 1/1 — Название клиента")
    await callback.answer()


@router.message(ClientCreate.name)
async def add_client_name(message: Message, session: AsyncSession, state: FSMContext) -> None:
    client = await create_client(session, name=message.text or "Client")
    await state.clear()
    forms_count, leads_today = await get_client_counts(session, client.id)
    await message.answer(format_client_card(client, forms_count, leads_today), reply_markup=client_card_kb(client.id))


@router.callback_query(lambda c: c.data == "clients:list")
async def clients_list(callback: CallbackQuery, session: AsyncSession) -> None:
    clients = await list_clients(session)
    if not clients:
        await callback.message.edit_text("👥 Клиентов пока нет.", reply_markup=clients_menu_kb())
        await callback.answer()
        return
    rows = [
        [InlineKeyboardButton(text=f"{client.name} ({client.status})", callback_data=f"clients:card:{client.id}")]
        for client in clients[:30]
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="clients:menu")])
    await callback.message.edit_text("📋 <b>Список клиентов</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("clients:card:"))
async def client_card(callback: CallbackQuery, session: AsyncSession) -> None:
    client_id = int(callback.data.split(":")[-1])
    client = await get_client_by_id(session, client_id)
    if not client:
        await callback.answer("Клиент не найден", show_alert=True)
        return
    forms_count, leads_today = await get_client_counts(session, client.id)
    await callback.message.edit_text(format_client_card(client, forms_count, leads_today), reply_markup=client_card_kb(client.id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("clients:add_tg:"))
async def add_tg_start(callback: CallbackQuery, state: FSMContext) -> None:
    client_id = int(callback.data.split(":")[-1])
    await state.update_data(client_id=client_id)
    await state.set_state(ClientAddTelegram.telegram_id)
    await callback.message.edit_text("Отправь Telegram ID клиента.")
    await callback.answer()


@router.message(ClientAddTelegram.telegram_id)
async def add_tg_finish(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    client_id = int(data["client_id"])
    client = await add_client_telegram_id(session, client_id, message.text or "")
    await state.clear()
    if not client:
        await message.answer("Клиент не найден.", reply_markup=clients_menu_kb())
        return
    forms_count, leads_today = await get_client_counts(session, client.id)
    await message.answer(format_client_card(client, forms_count, leads_today), reply_markup=client_card_kb(client.id))


@router.callback_query(lambda c: c.data and c.data.startswith("clients:add_email:"))
async def add_email_start(callback: CallbackQuery, state: FSMContext) -> None:
    client_id = int(callback.data.split(":")[-1])
    await state.update_data(client_id=client_id)
    await state.set_state(ClientAddEmail.email)
    await callback.message.edit_text("Отправь email клиента.")
    await callback.answer()


@router.message(ClientAddEmail.email)
async def add_email_finish(message: Message, session: AsyncSession, state: FSMContext) -> None:
    email = (message.text or "").strip()
    if not is_valid_email(email):
        await message.answer("Email выглядит неверно. Отправь нормальный email.")
        return
    data = await state.get_data()
    client_id = int(data["client_id"])
    client = await add_client_email(session, client_id, email)
    await state.clear()
    if not client:
        await message.answer("Клиент не найден.", reply_markup=clients_menu_kb())
        return
    forms_count, leads_today = await get_client_counts(session, client.id)
    await message.answer(format_client_card(client, forms_count, leads_today), reply_markup=client_card_kb(client.id))


@router.callback_query(F.data.in_({"clients:search"}))
async def clients_search_info(callback: CallbackQuery) -> None:
    await callback.message.edit_text("🔍 Поиск: пока открой список клиентов и выбери нужного.", reply_markup=clients_menu_kb())
    await callback.answer()
