from __future__ import annotations
import asyncio
from datetime import datetime
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.funnel_kb import (
    funnel_card_kb, funnel_join_notify_kb, funnel_list_kb, funnel_sendold_options_kb,
    recipients_list_kb, sheet_choice_kb, skip_kb,
)
from app.bot.keyboards.leads_kb import leads_list_kb
from app.services.apps_script_generator import generate_apps_script
from app.services.client_recipient_service import (
    get_or_create_recipient, list_recipients, remove_recipient, send_leads_to_recipient,
)
from app.services.funnel_form_service import (
    create_funnel_form, get_form_by_id, list_forms, toggle_form_status,
)
from app.services.lead_service import list_leads_by_funnel
from app.utils.formatters import fmt_dt, format_funnel_card
from config import ADMIN_IDS, BOT_USERNAME

router = Router(name="funnel")


# ── FSM STATES ──────────────────────────────────────────────
class FunnelFSM(StatesGroup):
    form_name = State()
    tag = State()
    fb_form_id = State()
    fb_page_id = State()
    sheet_choice = State()
    sheet_id = State()
    sheet_name = State()


# ── LIST & CREATE ────────────────────────────────────────────

@router.callback_query(lambda c: c.data == "funnel:list")
async def funnel_list(callback: CallbackQuery, session: AsyncSession) -> None:
    forms = await list_forms(session)
    text = f"📋 <b>Мои лид-формы</b>\n\nВсего: {len(forms)}"
    await callback.message.edit_text(text, reply_markup=funnel_list_kb(forms))
    await callback.answer()


@router.callback_query(lambda c: c.data == "funnel:create")
async def funnel_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(FunnelFSM.form_name)
    await callback.message.edit_text(
        "➕ <b>Создание лид-формы</b>\n\n"
        "<b>Шаг 1/4.</b> Как называется лид-форма?\n\n"
        "<i>Пример: SkyX PL 18-30</i>"
    )
    await callback.answer()


@router.message(FunnelFSM.form_name)
async def wizard_form_name(message: Message, state: FSMContext) -> None:
    await state.update_data(form_name=message.text.strip())
    await state.set_state(FunnelFSM.tag)
    await message.answer(
        "<b>Шаг 2/4.</b> Тег / оффер для сообщений?\n\n"
        "<i>Пример: SkyX / PL / 18-30 / preland</i>\n"
        "<i>Этот текст будет в каждом уведомлении о лиде.</i>"
    )


@router.message(FunnelFSM.tag)
async def wizard_tag(message: Message, state: FSMContext) -> None:
    await state.update_data(tag=message.text.strip())
    await state.set_state(FunnelFSM.fb_form_id)
    await message.answer(
        "<b>Шаг 3/4.</b> Facebook Form ID?\n\n"
        "<i>Найти: Meta Business Suite → Лид-формы → выбрать форму → ID в URL</i>\n"
        "<i>Пример: 941541071981</i>"
    )


@router.message(FunnelFSM.fb_form_id)
async def wizard_fb_form_id(message: Message, state: FSMContext) -> None:
    await state.update_data(fb_form_id=message.text.strip())
    await state.set_state(FunnelFSM.fb_page_id)
    await message.answer(
        "<b>Шаг 4/4.</b> Facebook Page ID? (необязательно)\n\n"
        "<i>Можно пропустить — нажми кнопку ниже.</i>",
        reply_markup=skip_kb(),
    )


@router.callback_query(lambda c: c.data == "wizard:skip")
async def wizard_skip_page_id(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(fb_page_id=None)
    await state.set_state(FunnelFSM.sheet_choice)
    await callback.message.edit_text(
        "Подключить <b>Google Sheet</b> для автозаписи лидов?",
        reply_markup=sheet_choice_kb(),
    )
    await callback.answer()


@router.message(FunnelFSM.fb_page_id)
async def wizard_fb_page_id(message: Message, state: FSMContext) -> None:
    await state.update_data(fb_page_id=message.text.strip())
    await state.set_state(FunnelFSM.sheet_choice)
    await message.answer(
        "Подключить <b>Google Sheet</b> для автозаписи лидов?",
        reply_markup=sheet_choice_kb(),
    )


@router.callback_query(lambda c: c.data == "wizard:sheet:skip")
async def wizard_sheet_skip(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.update_data(google_sheet_id=None, google_sheet_name="Leads")
    await _finish_wizard(callback, state, session)


@router.callback_query(lambda c: c.data == "wizard:sheet:yes")
async def wizard_sheet_yes(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FunnelFSM.sheet_id)
    await callback.message.edit_text(
        "📊 Введи <b>Google Sheet ID</b>:\n\n"
        "<i>Найти: открой таблицу → в URL между /d/ и /edit</i>\n"
        "<i>Пример: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms</i>"
    )
    await callback.answer()


@router.message(FunnelFSM.sheet_id)
async def wizard_sheet_id(message: Message, state: FSMContext) -> None:
    await state.update_data(google_sheet_id=message.text.strip())
    await state.set_state(FunnelFSM.sheet_name)
    await message.answer(
        "Название листа? (по умолчанию: Leads)\n\n"
        "<i>Нажми /skip или введи название</i>",
        reply_markup=skip_kb(),
    )


@router.message(FunnelFSM.sheet_name)
async def wizard_sheet_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    text = message.text.strip()
    if text.lower() in ("/skip", "пропустить", "skip"):
        text = "Leads"
    await state.update_data(google_sheet_name=text)
    # fake callback-like finish
    data = await state.get_data()
    await state.clear()
    form = await create_funnel_form(
        session,
        form_name=data["form_name"],
        tag=data.get("tag"),
        fb_form_id=data["fb_form_id"],
        fb_page_id=data.get("fb_page_id"),
        google_sheet_id=data.get("google_sheet_id"),
        google_sheet_name=data.get("google_sheet_name", "Leads"),
    )
    await message.answer(_form_created_text(form), reply_markup=funnel_card_kb(form.id, True))


async def _finish_wizard(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    await state.clear()
    form = await create_funnel_form(
        session,
        form_name=data["form_name"],
        tag=data.get("tag"),
        fb_form_id=data["fb_form_id"],
        fb_page_id=data.get("fb_page_id"),
        google_sheet_id=data.get("google_sheet_id"),
        google_sheet_name=data.get("google_sheet_name", "Leads"),
    )
    await callback.message.edit_text(_form_created_text(form), reply_markup=funnel_card_kb(form.id, True))
    await callback.answer()


def _form_created_text(form) -> str:
    sheet_status = f"✅ {form.google_sheet_id}" if form.google_sheet_id else "❌ не подключён"
    return (
        f"✅ <b>Лид-форма создана!</b>\n\n"
        f"Форма: <b>{form.form_name}</b>\n"
        f"Тег: {form.tag or '—'}\n"
        f"FB Form ID: <code>{form.fb_form_id}</code>\n"
        f"Verify Token: <code>{form.verify_token}</code>\n"
        f"Google Sheet: {sheet_status}\n\n"
        f"<b>Что дальше:</b>\n"
        f"1. Нажми <b>📋 Код Apps Script</b> — скопируй код\n"
        f"2. Вставь в Google Sheet → Extensions → Apps Script\n"
        f"3. Deploy → New deployment → Web App (Anyone)\n"
        f"4. Полученный URL → Meta → Webhooks → Callback URL\n"
        f"5. Verify Token: <code>{form.verify_token}</code>\n"
        f"6. Подпишись на поле <b>leadgen</b>\n"
        f"7. Отправь тестовый лид"
    )


# ── FORM CARD ────────────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("funnel:card:"))
async def funnel_card(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[2])
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена.", show_alert=True)
        return
    today = datetime.now().date().isoformat()
    all_leads = await list_leads_by_funnel(session, form_id)
    today_leads = [l for l in all_leads if l.created_at.date().isoformat() == today]
    recipients = await list_recipients(session, form_id)
    text = format_funnel_card(form, len(all_leads), len(today_leads), len(recipients))
    await callback.message.edit_text(text, reply_markup=funnel_card_kb(form_id, form.status == "active"))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:toggle:"))
async def funnel_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[2])
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена.", show_alert=True)
        return
    form = await toggle_form_status(session, form)
    status = "активна" if form.status == "active" else "выключена"
    await callback.answer(f"Форма {status}.", show_alert=True)
    # refresh card
    today = datetime.now().date().isoformat()
    all_leads = await list_leads_by_funnel(session, form_id)
    today_leads = [l for l in all_leads if l.created_at.date().isoformat() == today]
    recipients = await list_recipients(session, form_id)
    text = format_funnel_card(form, len(all_leads), len(today_leads), len(recipients))
    await callback.message.edit_text(text, reply_markup=funnel_card_kb(form_id, form.status == "active"))


# ── APPS SCRIPT CODE ─────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("funnel:code:"))
async def funnel_code(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[2])
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена.", show_alert=True)
        return
    code = generate_apps_script(form)
    # Send as a separate message (code too long for edit)
    await callback.message.answer(
        f"📋 <b>Код Apps Script для: {form.form_name}</b>\n\n"
        f"<code>{code}</code>"
    )
    await callback.answer()


# ── JOIN LINK ────────────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("funnel:joinlink:"))
async def funnel_joinlink(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[2])
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена.", show_alert=True)
        return
    link = f"https://t.me/{BOT_USERNAME}?start=join_{form.id}_{form.join_code}"
    await callback.message.edit_text(
        f"👥 <b>Подключение клиента к форме</b>\n\n"
        f"Форма: <b>{form.form_name}</b>\n"
        f"Тег: {form.tag or '—'}\n\n"
        f"Отправь клиенту эту ссылку:\n"
        f"<code>{link}</code>\n\n"
        f"Когда клиент нажмёт — он автоматически добавится в получатели.\n"
        f"Ты получишь уведомление и сможешь отправить ему старые заявки.",
        reply_markup=funnel_card_kb(form_id, form.status == "active"),
    )
    await callback.answer()


# ── RECIPIENTS LIST ──────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("funnel:recipients:"))
async def funnel_recipients(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[2])
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена.", show_alert=True)
        return
    recipients = await list_recipients(session, form_id)
    text = (
        f"👥 <b>Получатели: {form.form_name}</b>\n\n"
        f"Активных: {len(recipients)}"
    )
    await callback.message.edit_text(text, reply_markup=recipients_list_kb(recipients, form_id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:delrecip:"))
async def funnel_del_recipient(callback: CallbackQuery, session: AsyncSession) -> None:
    parts = callback.data.split(":")
    recipient_id = int(parts[2])
    form_id = int(parts[3])
    await remove_recipient(session, recipient_id)
    recipients = await list_recipients(session, form_id)
    form = await get_form_by_id(session, form_id)
    await callback.message.edit_text(
        f"👥 <b>Получатели: {form.form_name if form else '—'}</b>\n\nАктивных: {len(recipients)}",
        reply_markup=recipients_list_kb(recipients, form_id),
    )
    await callback.answer("Получатель удалён.")


# ── LEADS OF FORM ────────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("funnel:leads:"))
async def funnel_leads(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[2])
    leads = await list_leads_by_funnel(session, form_id, limit=30)
    if not leads:
        await callback.answer("Лидов нет.", show_alert=True)
        return
    await callback.message.edit_text(
        f"📥 Лиды формы (последние {len(leads)}):",
        reply_markup=leads_list_kb(leads, back_cb=f"funnel:card:{form_id}"),
    )
    await callback.answer()


# ── SEND OLD LEADS ───────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("funnel:sendold:"))
async def funnel_sendold(callback: CallbackQuery, session: AsyncSession) -> None:
    parts = callback.data.split(":")
    recipient_id = int(parts[2])
    mode = parts[3] if len(parts) > 3 else "choose"

    from app.models.client_recipient import ClientRecipient
    from sqlalchemy import select as sa_select
    recipient = (await session.execute(
        sa_select(ClientRecipient).where(ClientRecipient.id == recipient_id)
    )).scalar_one_or_none()
    if not recipient:
        await callback.answer("Получатель не найден.", show_alert=True)
        return

    if mode == "choose":
        await callback.message.edit_text(
            "Сколько старых лидов отправить?",
            reply_markup=funnel_sendold_options_kb(recipient_id),
        )
        await callback.answer()
        return

    if mode == "skip":
        await callback.answer("Ок, только новые заявки.", show_alert=True)
        return

    form_id = recipient.funnel_form_id
    limit = None if mode == "all" else 20
    leads = await list_leads_by_funnel(session, form_id, limit=limit)
    if not leads:
        await callback.answer("Лидов нет.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(
        f"⏳ Отправляю {len(leads)} лидов получателю...\n\nПожалуйста, подожди."
    )

    bot = callback.bot
    sent, errors = await send_leads_to_recipient(bot, recipient, leads)

    form = await get_form_by_id(session, form_id)
    name = recipient.first_name or recipient.telegram_username or str(recipient.telegram_user_id)
    await callback.message.edit_text(
        f"✅ <b>Отправка завершена</b>\n\n"
        f"Получатель: {name}\n"
        f"Форма: {form.form_name if form else '—'}\n\n"
        f"Отправлено: {sent}\n"
        f"Ошибок: {errors}",
        reply_markup=funnel_card_kb(form_id, form.status == "active" if form else True),
    )
