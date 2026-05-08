from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.delivery_rules_kb import delivery_rules_menu_kb, rule_card_kb
from app.bot.states.delivery_rule_states import DeliveryRuleCreate
from app.models.lead import SourceType
from app.services.client_service import get_client_by_id, list_clients
from app.services.delivery_service import create_delivery_rule, list_delivery_rules
from app.services.facebook_form_service import get_facebook_form_by_id, list_facebook_forms
from app.utils.formatters import load_json_list
from app.utils.validators import parse_int_list, parse_str_list

router = Router(name="delivery_rules")


@router.callback_query(lambda c: c.data == "rules:menu")
async def rules_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🔀 <b>Правила отправки</b>\n\nПравило = какая FB форма куда отправляет лиды.",
        reply_markup=delivery_rules_menu_kb(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "rules:add")
async def add_rule_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    forms = await list_facebook_forms(session, active_only=True)
    if not forms:
        await callback.answer("Сначала добавь FB форму", show_alert=True)
        return
    rows = [[InlineKeyboardButton(text=form.name, callback_data=f"rules:select_form:{form.id}")] for form in forms]
    await state.set_state(DeliveryRuleCreate.form_id)
    await callback.message.edit_text("Шаг 1/7 — выбери Facebook форму", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("rules:create_for_form:"))
async def add_rule_for_form(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    form_id = int(callback.data.split(":")[-1])
    form = await get_facebook_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена", show_alert=True)
        return
    await state.update_data(form_id=form_id)
    clients = await list_clients(session, active_only=True)
    rows = [[InlineKeyboardButton(text=client.name, callback_data=f"rules:select_client:{client.id}")] for client in clients]
    await state.set_state(DeliveryRuleCreate.client_id)
    await callback.message.edit_text("Шаг 2/7 — выбери клиента", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(DeliveryRuleCreate.form_id, lambda c: c.data and c.data.startswith("rules:select_form:"))
async def add_rule_select_form(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    form_id = int(callback.data.split(":")[-1])
    await state.update_data(form_id=form_id)
    clients = await list_clients(session, active_only=True)
    if not clients:
        await state.clear()
        await callback.answer("Сначала добавь клиента", show_alert=True)
        return
    rows = [[InlineKeyboardButton(text=client.name, callback_data=f"rules:select_client:{client.id}")] for client in clients]
    await state.set_state(DeliveryRuleCreate.client_id)
    await callback.message.edit_text("Шаг 2/7 — выбери клиента", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(DeliveryRuleCreate.client_id, lambda c: c.data and c.data.startswith("rules:select_client:"))
async def add_rule_client(callback: CallbackQuery, state: FSMContext) -> None:
    client_id = int(callback.data.split(":")[-1])
    await state.update_data(client_id=client_id)
    await state.set_state(DeliveryRuleCreate.send_to_admin)
    await callback.message.edit_text(
        "Шаг 3/7 — отправлять админу?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да", callback_data="rules:admin:yes")],
                [InlineKeyboardButton(text="❌ Нет", callback_data="rules:admin:no")],
            ]
        ),
    )
    await callback.answer()


@router.callback_query(DeliveryRuleCreate.send_to_admin, lambda c: c.data and c.data.startswith("rules:admin:"))
async def add_rule_admin(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(send_to_admin=callback.data.endswith(":yes"))
    await state.set_state(DeliveryRuleCreate.telegram_ids)
    await callback.message.edit_text("Шаг 4/7 — Telegram IDs через запятую или '-' чтобы пропустить")
    await callback.answer()


@router.message(DeliveryRuleCreate.telegram_ids)
async def add_rule_telegram(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    await state.update_data(telegram_ids=[] if text == "-" else [str(item) for item in parse_int_list(text)])
    await state.set_state(DeliveryRuleCreate.emails)
    await message.answer("Шаг 5/7 — Emails через запятую или '-' чтобы пропустить")


@router.message(DeliveryRuleCreate.emails)
async def add_rule_emails(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    await state.update_data(emails=[] if text == "-" else parse_str_list(text))
    await state.set_state(DeliveryRuleCreate.google_sheet_id)
    await message.answer("Шаг 6/7 — Google Sheet ID или '-' чтобы пропустить")


@router.message(DeliveryRuleCreate.google_sheet_id)
async def add_rule_finish(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    sheet_id = (message.text or "").strip()
    rule = await create_delivery_rule(
        session,
        source_type=SourceType.facebook_lead_form.value,
        source_id=int(data["form_id"]),
        client_id=int(data["client_id"]),
        send_to_admin=bool(data["send_to_admin"]),
        telegram_ids=data.get("telegram_ids", []),
        emails=data.get("emails", []),
        google_sheet_id=None if sheet_id == "-" else sheet_id,
    )
    await state.clear()
    await message.answer(_format_rule_card(rule), reply_markup=rule_card_kb(rule.id))


@router.callback_query(lambda c: c.data == "rules:list")
async def rules_list(callback: CallbackQuery, session: AsyncSession) -> None:
    rules = await list_delivery_rules(session)
    if not rules:
        await callback.message.edit_text("🔀 Правил пока нет.", reply_markup=delivery_rules_menu_kb())
        await callback.answer()
        return
    rows = [[InlineKeyboardButton(text=f"Правило #{rule.id} → client {rule.client_id}", callback_data=f"rules:card:{rule.id}")] for rule in rules]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="rules:menu")])
    await callback.message.edit_text("📋 <b>Список правил</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("rules:card:"))
async def rule_card(callback: CallbackQuery, session: AsyncSession) -> None:
    rule_id = int(callback.data.split(":")[-1])
    rules = await list_delivery_rules(session)
    rule = next((item for item in rules if item.id == rule_id), None)
    if not rule:
        await callback.answer("Правило не найдено", show_alert=True)
        return
    await callback.message.edit_text(_format_rule_card(rule), reply_markup=rule_card_kb(rule.id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("rules:test"))
async def rules_test_info(callback: CallbackQuery) -> None:
    await callback.answer("Тест правила делай через FB Формы → Тестовый лид.", show_alert=True)


def _format_rule_card(rule: object) -> str:
    telegram_ids = ", ".join(str(item) for item in load_json_list(rule.telegram_ids_json)) or "-"
    emails = ", ".join(str(item) for item in load_json_list(rule.emails_json)) or "-"
    return (
        f"🔀 <b>Правило #{rule.id}</b>\n\n"
        "Если лид пришёл из:\n"
        f"FB Form ID: {rule.source_id}\n\n"
        "Клиент:\n"
        f"Client #{rule.client_id}\n\n"
        "Отправлять:\n"
        f"{'✅' if rule.send_to_admin else '⬜'} Admin Telegram\n"
        f"{'✅' if telegram_ids != '-' else '⬜'} Client Telegram: {telegram_ids}\n"
        f"{'✅' if emails != '-' else '⬜'} Email: {emails}\n"
        f"{'✅' if rule.google_sheet_id else '⬜'} Google Sheet"
    )
