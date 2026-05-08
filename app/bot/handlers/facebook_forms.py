from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.facebook_forms_kb import facebook_form_card_kb, facebook_forms_menu_kb
from app.bot.keyboards.main_kb import back_home_kb
from app.bot.states.facebook_form_states import FacebookFormCreate
from app.models.lead import SourceType
from app.services.client_service import list_clients
from app.services.delivery_service import create_delivery_rule
from app.services.facebook_form_service import (
    create_facebook_form,
    get_facebook_form_by_id,
    get_form_today_counts,
    list_facebook_forms,
    toggle_facebook_form_status,
)
from app.services.facebook_lead_service import create_lead_from_facebook
from app.services.lead_service import get_lead_by_id
from app.utils.formatters import format_form_card, load_json_list
from config import FACEBOOK_VERIFY_TOKEN, PUBLIC_BASE_URL

router = Router(name="facebook_forms")


@router.callback_query(lambda c: c.data == "fbforms:menu")
async def fbforms_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    forms = await list_facebook_forms(session)
    active = sum(1 for form in forms if form.status == "active")
    leads_today = 0
    for form in forms:
        leads_today += (await get_form_today_counts(session, form.id))["leads"]
    await callback.message.edit_text(
        f"📋 <b>Facebook формы</b>\n\nПодключено: {len(forms)}\nАктивных: {active}\nЛидов сегодня: {leads_today}",
        reply_markup=facebook_forms_menu_kb(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "fbforms:add")
async def add_form_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FacebookFormCreate.name)
    await callback.message.edit_text("Шаг 1/5 — Название формы")
    await callback.answer()


@router.message(FacebookFormCreate.name)
async def add_form_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await state.set_state(FacebookFormCreate.fb_page_id)
    await message.answer("Шаг 2/5 — FB Page ID")


@router.message(FacebookFormCreate.fb_page_id)
async def add_form_page(message: Message, state: FSMContext) -> None:
    await state.update_data(fb_page_id=message.text)
    await state.set_state(FacebookFormCreate.fb_form_id)
    await message.answer("Шаг 3/5 — FB Form ID")


@router.message(FacebookFormCreate.fb_form_id)
async def add_form_form_id(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.update_data(fb_form_id=message.text)
    clients = await list_clients(session, active_only=True)
    if not clients:
        await state.clear()
        await message.answer("Сначала создай клиента: 👥 Клиенты → ➕ Добавить клиента", reply_markup=facebook_forms_menu_kb())
        return
    rows = [[InlineKeyboardButton(text=client.name, callback_data=f"fbforms:select_client:{client.id}")] for client in clients]
    await state.set_state(FacebookFormCreate.client_id)
    await message.answer("Шаг 4/5 — Клиент", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(FacebookFormCreate.client_id, lambda c: c.data and c.data.startswith("fbforms:select_client:"))
async def add_form_client(callback: CallbackQuery, state: FSMContext) -> None:
    client_id = int(callback.data.split(":")[-1])
    await state.update_data(client_id=client_id)
    await state.set_state(FacebookFormCreate.offer_name)
    await callback.message.edit_text("Шаг 5/5 — Оффер / заметка")
    await callback.answer()


@router.message(FacebookFormCreate.offer_name)
async def add_form_finish(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    form = await create_facebook_form(
        session,
        name=data["name"],
        fb_page_id=data["fb_page_id"],
        fb_form_id=data["fb_form_id"],
        client_id=int(data["client_id"]),
        offer_name=message.text,
    )
    await create_delivery_rule(
        session,
        source_type=SourceType.facebook_lead_form.value,
        source_id=form.id,
        client_id=form.client_id,
        send_to_admin=True,
        telegram_ids=[],
        emails=[],
    )
    await state.clear()
    await message.answer(
        "✅ <b>FB форма добавлена</b>\n\n"
        f"Название: {form.name}\n"
        f"FB Form ID: {form.fb_form_id}\n"
        f"Клиент ID: {form.client_id}\n\n"
        "Теперь настрой, куда отправлять лиды.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔀 Настроить отправку", callback_data=f"rules:create_for_form:{form.id}")],
                [InlineKeyboardButton(text="🧪 Тестовый лид", callback_data=f"fbforms:test:{form.id}")],
                [InlineKeyboardButton(text="🏠 Главное", callback_data="main:menu")],
            ]
        ),
    )


@router.callback_query(lambda c: c.data == "fbforms:list")
async def fbforms_list(callback: CallbackQuery, session: AsyncSession) -> None:
    forms = await list_facebook_forms(session)
    if not forms:
        await callback.message.edit_text("📋 FB форм пока нет.", reply_markup=facebook_forms_menu_kb())
        await callback.answer()
        return
    rows = [[InlineKeyboardButton(text=f"{form.name} ({form.fb_form_id})", callback_data=f"fbforms:card:{form.id}")] for form in forms[:30]]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="fbforms:menu")])
    await callback.message.edit_text("📋 <b>Список FB форм</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("fbforms:card:"))
async def fbform_card(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[-1])
    form = await get_facebook_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена", show_alert=True)
        return
    counts = await get_form_today_counts(session, form.id)
    await callback.message.edit_text(
        format_form_card(form, counts["leads"], counts["delivered"], counts["errors"]),
        reply_markup=facebook_form_card_kb(form.id),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("fbforms:toggle:"))
async def fbform_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[-1])
    form = await toggle_facebook_form_status(session, form_id)
    if not form:
        await callback.answer("Форма не найдена", show_alert=True)
        return
    await callback.answer(f"Статус: {form.status}")
    counts = await get_form_today_counts(session, form.id)
    await callback.message.edit_text(
        format_form_card(form, counts["leads"], counts["delivered"], counts["errors"]),
        reply_markup=facebook_form_card_kb(form.id),
    )


@router.callback_query(lambda c: c.data == "fbforms:webhook")
async def webhook_instruction(callback: CallbackQuery) -> None:
    text = (
        "🔗 <b>Webhook инструкция</b>\n\n"
        "Callback URL:\n"
        f"{PUBLIC_BASE_URL}/webhooks/facebook\n\n"
        "Verify Token:\n"
        f"{FACEBOOK_VERIFY_TOKEN}\n\n"
        "Meta Developers: Webhooks → Page → leadgen → Verify and Save."
    )
    await callback.message.edit_text(text, reply_markup=back_home_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data and (c.data == "fbforms:test" or c.data.startswith("fbforms:test:")))
async def test_lead(callback: CallbackQuery, session: AsyncSession) -> None:
    forms = await list_facebook_forms(session, active_only=True)
    if callback.data and callback.data.startswith("fbforms:test:"):
        form = await get_facebook_form_by_id(session, int(callback.data.split(":")[-1]))
    else:
        form = forms[0] if forms else None
    if not form:
        await callback.answer("Сначала добавь FB форму", show_alert=True)
        return
    event = {"leadgen_id": f"test_{form.id}", "form_id": form.fb_form_id, "page_id": form.fb_page_id}
    raw = {
        "id": event["leadgen_id"],
        "field_data": [
            {"name": "full_name", "values": ["Test Lead"]},
            {"name": "phone_number", "values": ["+380000000000"]},
            {"name": "email", "values": ["test@example.com"]},
        ],
    }
    lead = await create_lead_from_facebook(session, event, raw_details=raw)
    if lead:
        await callback.message.edit_text(
            f"🧪 Тестовый лид создан: #{lead.id}\n\nОткрой раздел 📥 Лиды или повтори доставку из карточки.",
            reply_markup=facebook_forms_menu_kb(),
        )
    await callback.answer()
