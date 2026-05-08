from datetime import datetime, timedelta

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.prelands_kb import preland_card_kb, prelands_menu_kb
from app.bot.states.preland_states import PrelandCreate
from app.services.client_service import list_clients
from app.services.preland_service import create_preland, get_preland_by_id, list_prelands
from app.services.preland_tracking_service import (
    get_preland_button_stats,
    get_preland_stats,
    today_range,
    track_button_click,
    track_page_view,
)
from app.services.stats_service import preland_visits_clicks_ctr
from app.utils.formatters import format_preland_card, tracking_code_text
from app.utils.validators import is_valid_slug, normalize_slug

router = Router(name="prelands")


@router.callback_query(lambda c: c.data == "prelands:menu")
async def prelands_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    stats = await preland_visits_clicks_ctr(session)
    await callback.message.edit_text(
        "🌐 <b>Prelands</b>\n\n"
        "Сегодня:\n"
        f"Visits: {stats['visits']}\n"
        f"Clicks: {stats['clicks']}\n"
        f"CTR: {stats['ctr']}%",
        reply_markup=prelands_menu_kb(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "prelands:add")
async def add_preland_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PrelandCreate.name)
    await callback.message.edit_text("Шаг 1/5 — name")
    await callback.answer()


@router.message(PrelandCreate.name)
async def add_preland_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await state.set_state(PrelandCreate.slug)
    suggested = normalize_slug(message.text or "")
    await message.answer(f"Шаг 2/5 — slug\n\nНапример: {suggested or 'remote-ua'}")


@router.message(PrelandCreate.slug)
async def add_preland_slug(message: Message, state: FSMContext) -> None:
    slug = normalize_slug(message.text or "")
    if not is_valid_slug(slug):
        await message.answer("Slug должен быть латиницей: remote-ua, work_pl_1.")
        return
    await state.update_data(slug=slug)
    await state.set_state(PrelandCreate.url)
    await message.answer("Шаг 3/5 — URL")


@router.message(PrelandCreate.url)
async def add_preland_url(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.update_data(url=message.text)
    clients = await list_clients(session, active_only=True)
    rows = [[InlineKeyboardButton(text=client.name, callback_data=f"prelands:select_client:{client.id}")] for client in clients]
    rows.append([InlineKeyboardButton(text="Пропустить", callback_data="prelands:select_client:0")])
    await state.set_state(PrelandCreate.client_id)
    await message.answer("Шаг 4/5 — select client", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(PrelandCreate.client_id, lambda c: c.data and c.data.startswith("prelands:select_client:"))
async def add_preland_client(callback: CallbackQuery, state: FSMContext) -> None:
    client_id = int(callback.data.split(":")[-1])
    await state.update_data(client_id=None if client_id == 0 else client_id)
    await state.set_state(PrelandCreate.offer_name)
    await callback.message.edit_text("Шаг 5/5 — offer_name")
    await callback.answer()


@router.message(PrelandCreate.offer_name)
async def add_preland_finish(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    preland = await create_preland(
        session,
        name=data["name"],
        slug=data["slug"],
        url=data["url"],
        client_id=data.get("client_id"),
        offer_name=message.text,
    )
    await state.clear()
    start, end = today_range()
    stats = await get_preland_stats(session, preland.id, start, end)
    buttons = await get_preland_button_stats(session, preland.id, start, end)
    await message.answer(format_preland_card(preland, stats, buttons), reply_markup=preland_card_kb(preland.id, preland.slug))


@router.callback_query(lambda c: c.data == "prelands:list")
async def prelands_list(callback: CallbackQuery, session: AsyncSession) -> None:
    prelands = await list_prelands(session)
    if not prelands:
        await callback.message.edit_text("🌐 Prelands пока нет.", reply_markup=prelands_menu_kb())
        await callback.answer()
        return
    rows = [[InlineKeyboardButton(text=f"{item.name} ({item.slug})", callback_data=f"prelands:card:{item.id}")] for item in prelands[:30]]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="prelands:menu")])
    await callback.message.edit_text("📋 <b>Список prelands</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("prelands:card:"))
async def preland_card(callback: CallbackQuery, session: AsyncSession) -> None:
    preland = await get_preland_by_id(session, int(callback.data.split(":")[-1]))
    if not preland:
        await callback.answer("Preland не найден", show_alert=True)
        return
    start, end = today_range()
    stats = await get_preland_stats(session, preland.id, start, end)
    buttons = await get_preland_button_stats(session, preland.id, start, end)
    await callback.message.edit_text(
        format_preland_card(preland, stats, buttons),
        reply_markup=preland_card_kb(preland.id, preland.slug),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "prelands:tracking_code" or (c.data and c.data.startswith("prelands:code:")))
async def tracking_code(callback: CallbackQuery) -> None:
    slug = "PRELAND_SLUG"
    if callback.data and callback.data.startswith("prelands:code:"):
        slug = callback.data.split(":", 2)[-1]
    await callback.message.edit_text(tracking_code_text(slug), reply_markup=prelands_menu_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("prelands:test_view:"))
async def test_page_view(callback: CallbackQuery, session: AsyncSession) -> None:
    preland = await get_preland_by_id(session, int(callback.data.split(":")[-1]))
    if not preland:
        await callback.answer("Preland не найден", show_alert=True)
        return
    await track_page_view(session, preland.slug, {"url": preland.url, "referer": "telegram_test"}, ip="127.0.0.1")
    await callback.answer("page_view записан")


@router.callback_query(lambda c: c.data and c.data.startswith("prelands:test_click:"))
async def test_click(callback: CallbackQuery, session: AsyncSession) -> None:
    preland = await get_preland_by_id(session, int(callback.data.split(":")[-1]))
    if not preland:
        await callback.answer("Preland не найден", show_alert=True)
        return
    await track_button_click(session, preland.slug, "main_cta", {"url": preland.url}, ip="127.0.0.1")
    await callback.answer("button_click записан")


@router.callback_query(lambda c: c.data and c.data.startswith("prelands:stats_"))
async def preland_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    parts = callback.data.split(":")
    mode = parts[1].split("_")[-1]
    preland_id = int(parts[-1])
    preland = await get_preland_by_id(session, preland_id)
    if not preland:
        await callback.answer("Preland не найден", show_alert=True)
        return
    end = datetime.utcnow()
    if mode == "today":
        start, end = today_range()
    elif mode == "7":
        start = end - timedelta(days=7)
    else:
        start = end - timedelta(days=30)
    stats = await get_preland_stats(session, preland.id, start, end)
    buttons = await get_preland_button_stats(session, preland.id, start, end)
    await callback.message.edit_text(format_preland_card(preland, stats, buttons), reply_markup=preland_card_kb(preland.id, preland.slug))
    await callback.answer()


@router.callback_query(lambda c: c.data == "prelands:test")
async def prelands_test_info(callback: CallbackQuery) -> None:
    await callback.answer("Открой карточку preland и нажми тест page_view/click.", show_alert=True)
