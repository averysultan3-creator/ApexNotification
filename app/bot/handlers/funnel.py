from __future__ import annotations

from datetime import datetime
from html import escape

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.funnel_kb import (
    funnel_card_kb,
    funnel_created_kb,
    funnel_list_kb,
    funnel_sendold_menu_kb,
    funnel_stats_kb,
    recipients_list_kb,
    sheet_name_kb,
    skip_kb,
)
from app.bot.keyboards.leads_kb import leads_list_kb
from app.models.client_recipient import ClientRecipient
from app.services.apps_script_generator import generate_apps_script
from app.services.client_recipient_service import list_recipients, remove_recipient
from app.services.delivery_service import deliver_lead
from app.services.funnel_form_service import (
    create_funnel_form,
    get_form_by_id,
    list_forms,
    toggle_form_status,
)
from app.services.google_sheet_service import send_old_leads_to_recipient
from app.services.lead_service import create_lead, list_leads_by_funnel
from app.services.stats_service import funnel_stats_today
from app.utils.formatters import format_funnel_card
from app.bot.keyboards.main_kb import main_menu_kb
from config import BOT_USERNAME, FACEBOOK_PAGE_ACCESS_TOKEN, FACEBOOK_GRAPH_VERSION
from app.utils.facebook import graph_lead_url

router = Router(name="funnel")


class FunnelFSM(StatesGroup):
    form_name = State()
    tag = State()
    fb_form_id = State()
    sheet_id = State()
    sheet_name = State()
    rename = State()
    edit_tag = State()


def _part_int(data: str | None, index: int) -> int | None:
    try:
        return int((data or "").split(":")[index])
    except (IndexError, ValueError):
        return None


def _chunks(text: str, size: int = 3200) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


async def _show_form_card(callback: CallbackQuery, session: AsyncSession, form_id: int) -> None:
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("оронка не найдена.", show_alert=True)
        return

    stats = await funnel_stats_today(session, form_id)
    leads = await list_leads_by_funnel(session, form_id)
    recipients = await list_recipients(session, form_id)
    text = format_funnel_card(
        form,
        leads_total=len(leads),
        leads_today=stats["leads_today"],
        delivered_today=stats["delivered_today"],
        errors_today=stats["errors_today"],
        recipients_count=len(recipients),
    )
    await callback.message.edit_text(
        text,
        reply_markup=funnel_card_kb(form_id, form.status == "active"),
    )


@router.callback_query(lambda c: c.data == "funnel:list")
async def funnel_list(callback: CallbackQuery, session: AsyncSession) -> None:
    forms = await list_forms(session)
    await callback.message.edit_text(
        f"<b>Воронки</b>\n\nВсего: {len(forms)}",
        reply_markup=funnel_list_kb(forms),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "funnel:create")
async def funnel_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(FunnelFSM.form_name)
    await callback.message.edit_text(
        "<b>Новая воронка</b>\n\nШаг 1/5. Отправьте название воронки.\n/cancel — отмена"
    )
    await callback.answer()


@router.message(
    lambda m: m.text and m.text.strip() == "/cancel",
    FunnelFSM.form_name,
)
@router.message(
    lambda m: m.text and m.text.strip() == "/cancel",
    FunnelFSM.tag,
)
@router.message(
    lambda m: m.text and m.text.strip() == "/cancel",
    FunnelFSM.fb_form_id,
)
@router.message(
    lambda m: m.text and m.text.strip() == "/cancel",
    FunnelFSM.sheet_id,
)
@router.message(
    lambda m: m.text and m.text.strip() == "/cancel",
    FunnelFSM.sheet_name,
)
async def wizard_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_kb())


@router.callback_query(lambda c: c.data == "wizard:cancel")
async def wizard_cancel_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await callback.message.edit_text("Отменено.", reply_markup=main_menu_kb())
    except Exception:
        await callback.message.answer("Отменено.", reply_markup=main_menu_kb())
    await callback.answer()


@router.message(FunnelFSM.form_name)
async def wizard_form_name(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip():
        await message.answer("Название обязательно.")
        return
    await state.update_data(form_name=message.text.strip())
    await state.set_state(FunnelFSM.tag)
    await message.answer("Шаг 2/5. Отправьте тег/название оффера.")


@router.message(FunnelFSM.tag)
async def wizard_tag(message: Message, state: FSMContext) -> None:
    await state.update_data(tag=(message.text or "").strip() or None)
    await state.set_state(FunnelFSM.fb_form_id)
    await message.answer(
        "Шаг 3/5. Facebook Form ID или пропустите (если только Google Sheet).",
        reply_markup=skip_kb(),
    )


@router.message(FunnelFSM.fb_form_id)
async def wizard_fb_form_id(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    # Allow skipping FB Form ID for pure Google-Sheet funnels
    if text in ("", "-", "/skip", "skip"):
        # Generate unique placeholder so DB unique constraint is satisfied
        import secrets
        fb_form_id = f"gsheet_{secrets.token_hex(6)}"
    else:
        fb_form_id = text
    await state.update_data(fb_form_id=fb_form_id)
    await state.set_state(FunnelFSM.sheet_id)
    await message.answer(
        "Шаг 4/5. Google Sheet ID или пропустите.",
        reply_markup=skip_kb(),
    )


@router.callback_query(lambda c: c.data == "wizard:skip")
async def wizard_skip(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    current = await state.get_state()
    if current == FunnelFSM.fb_form_id.state:
        import secrets
        await state.update_data(fb_form_id=f"gsheet_{secrets.token_hex(6)}")
        await state.set_state(FunnelFSM.sheet_id)
        try:
            await callback.message.edit_text(
                "Шаг 4/5. Google Sheet ID или пропустите.",
                reply_markup=skip_kb(),
            )
        except Exception:
            await callback.message.answer(
                "Шаг 4/5. Google Sheet ID или пропустите.",
                reply_markup=skip_kb(),
            )
        await callback.answer()
        return
    # Default: skip Sheet ID → finish wizard with no Sheet
    await state.update_data(google_sheet_id=None, google_sheet_name="Leads")
    await _finish_wizard_cb(callback, state, session)


@router.message(FunnelFSM.sheet_id)
async def wizard_sheet_id(message: Message, state: FSMContext) -> None:
    await state.update_data(google_sheet_id=(message.text or "").strip() or None)
    await state.set_state(FunnelFSM.sheet_name)
    await message.answer(
        "Шаг 5/5. Имя вкладки в Sheet (например Sheet1 / Лист1 / Leads).",
        reply_markup=sheet_name_kb(),
    )


@router.message(FunnelFSM.sheet_name)
async def wizard_sheet_name_msg(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    await state.update_data(google_sheet_name=(message.text or "").strip() or "Leads")
    await _finish_wizard_msg(message, state, session)


@router.callback_query(lambda c: c.data and c.data.startswith("wizard:sheetname:"))
async def wizard_sheet_name_cb(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    name = (callback.data or "").split(":", 2)[2] or "Leads"
    await state.update_data(google_sheet_name=name)
    await _finish_wizard_cb(callback, state, session)


async def _create_form_from_state(state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await state.clear()
    return await create_funnel_form(
        session,
        form_name=data["form_name"],
        tag=data.get("tag"),
        fb_form_id=data["fb_form_id"],
        google_sheet_id=data.get("google_sheet_id"),
        google_sheet_name=data.get("google_sheet_name") or "Leads",
    )


async def _finish_wizard_msg(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    form = await _create_form_from_state(state, session)
    await message.answer(_form_created_text(form), reply_markup=funnel_created_kb(form.id))


async def _finish_wizard_cb(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    form = await _create_form_from_state(state, session)
    await callback.message.edit_text(
        _form_created_text(form),
        reply_markup=funnel_created_kb(form.id),
    )
    await callback.answer()


def _form_created_text(form) -> str:
    sheet_status = form.google_sheet_id or "не подключен"
    return (
        "<b>✅ Воронка создана</b>\n\n"
        f"Название: <b>{escape(form.form_name)}</b>\n"
        f"Тег: {escape(form.tag or '-')}\n"
        f"FB Form ID: <code>{escape(form.fb_form_id)}</code>\n"
        f"Google Sheet: <code>{escape(sheet_status)}</code>\n\n"
        "Дальше: скачайте код для Google Sheet, пригласите клиентов, отправьте тестовый лид."
    )


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:card:"))
async def funnel_card(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    await _show_form_card(callback, session, form_id)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:toggle:"))
async def funnel_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("оронка не найдена.", show_alert=True)
        return
    await toggle_form_status(session, form)
    await _show_form_card(callback, session, form_id)
    await callback.answer("Status updated.", show_alert=True)


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:code:"))
async def funnel_code(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("оронка не найдена.", show_alert=True)
        return
    code = generate_apps_script(form)
    file = BufferedInputFile(code.encode("utf-8"), filename=f"apex_{form.id}.txt")
    caption = (
        f"<b>Apps Script: {escape(form.form_name)}</b>\n\n"
        "1. Google Sheet → Расширения → Apps Script\n"
        "2. Удалите весь код по умолчанию и вставьте содержимое файла\n"
        "3. Сохраните (Ctrl+S)\n"
        "4. Запустите <code>setup</code> → разрешите доступ\n"
        "5. Запустите <code>testConnection</code> для проверки"
    )
    await callback.message.answer_document(file, caption=caption)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:stats:"))
async def funnel_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("оронка не найдена.", show_alert=True)
        return
    stats = await funnel_stats_today(session, form_id)
    leads = await list_leads_by_funnel(session, form_id)
    recipients = await list_recipients(session, form_id)
    text = (
        f"<b>Статистика: {escape(form.form_name)}</b>\n\n"
        f"Всего лидов: {len(leads)}\n"
        f"Сегодня лидов: {stats['leads_today']}\n"
        f"Сегодня доставлено: {stats['delivered_today']}\n"
        f"Сегодня ошибок: {stats['errors_today']}\n"
        f"Получатели: {len(recipients)}"
    )
    await callback.message.edit_text(text, reply_markup=funnel_stats_kb(form_id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:test:"))
async def funnel_test(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("оронка не найдена.", show_alert=True)
        return
    marker = int(datetime.utcnow().timestamp() * 1000)
    lead = await create_lead(
        session,
        funnel_form_id=form.id,
        fb_lead_id=f"test_{form.id}_{marker}",
        fb_form_id=form.fb_form_id,
        fb_page_id=form.fb_page_id,
        full_name="Test User",
        phone="+10000000000",
        email="test@example.com",
        tag=form.tag,
        raw_data_json='{"source":"telegram_test"}',
    )
    await session.refresh(lead, attribute_names=["funnel_form"])
    await deliver_lead(session, callback.bot, lead)
    await callback.message.edit_text(
        f"<b>Тестовый лид #{lead.id} создан</b>\n\nВоронка: {escape(form.form_name)}",
        reply_markup=funnel_card_kb(form_id, form.status == "active"),
    )
    await callback.answer("Тестовый лид отправлен.", show_alert=True)


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:edittag:"))
async def funnel_edittag_start(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Некорректный запрос.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Воронка не найдена.", show_alert=True)
        return
    await state.clear()
    await state.update_data(edit_tag_form_id=form_id)
    await state.set_state(FunnelFSM.edit_tag)
    current = escape(form.tag or '—')
    try:
        await callback.message.edit_text(
            f"<b>🏷 Изменить тег</b>\n\nТекущий тег: <b>{current}</b>\n\nОтправьте новый тег или /cancel"
        )
    except Exception:
        await callback.message.answer(
            f"<b>🏷 Изменить тег</b>\n\nТекущий тег: <b>{current}</b>\n\nОтправьте новый тег или /cancel"
        )
    await callback.answer()


@router.message(
    lambda m: m.text and m.text.strip() == "/cancel",
    FunnelFSM.edit_tag,
)
async def funnel_edittag_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_kb())


@router.message(FunnelFSM.edit_tag)
async def funnel_edittag_apply(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    new_tag = (message.text or "").strip()
    if not new_tag:
        await message.answer("Тег не может быть пустым.")
        return
    data = await state.get_data()
    form_id = data.get("edit_tag_form_id")
    await state.clear()
    if form_id is None:
        await message.answer("Не найдена воронка.", reply_markup=main_menu_kb())
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await message.answer("Воронка не найдена.", reply_markup=main_menu_kb())
        return
    form.tag = new_tag
    await session.flush()
    await message.answer(
        f"✅ Тег обновлён: <b>{escape(new_tag)}</b>",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:rename:"))
async def funnel_rename_start(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Некорректный запрос.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Воронка не найдена.", show_alert=True)
        return
    await state.clear()
    await state.update_data(rename_form_id=form_id)
    await state.set_state(FunnelFSM.rename)
    try:
        await callback.message.edit_text(
            f"<b>✏\ufe0f Переименование</b>\n\nТекущее название: <b>{escape(form.form_name)}</b>\n\nОтправьте новое название или /cancel"
        )
    except Exception:
        await callback.message.answer(
            f"<b>✏\ufe0f Переименование</b>\n\nТекущее название: <b>{escape(form.form_name)}</b>\n\nОтправьте новое название или /cancel"
        )
    await callback.answer()


@router.message(
    lambda m: m.text and m.text.strip() == "/cancel",
    FunnelFSM.rename,
)
async def funnel_rename_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_kb())


@router.message(FunnelFSM.rename)
async def funnel_rename_apply(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    new_name = (message.text or "").strip()
    if not new_name:
        await message.answer("Название не может быть пустым.")
        return
    if len(new_name) > 200:
        await message.answer("Слишком длинное название (макс 200 символов).")
        return
    data = await state.get_data()
    form_id = data.get("rename_form_id")
    await state.clear()
    if form_id is None:
        await message.answer("Не найдена воронка.", reply_markup=main_menu_kb())
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await message.answer("Воронка не найдена.", reply_markup=main_menu_kb())
        return
    old_name = form.form_name
    form.form_name = new_name
    await session.flush()
    # Notify all recipients about rename
    recipients = await list_recipients(session, form_id)
    notify_text = (
        f"ℹ\ufe0f Воронка переименована:\n"
        f"<s>{escape(old_name)}</s> → <b>{escape(new_name)}</b>"
    )
    for r in recipients:
        try:
            await message.bot.send_message(r.telegram_user_id, notify_text)
        except Exception:
            pass
    stats = await funnel_stats_today(session, form_id)
    leads = await list_leads_by_funnel(session, form_id)
    text = format_funnel_card(
        form,
        leads_total=len(leads),
        leads_today=stats["leads_today"],
        delivered_today=stats["delivered_today"],
        errors_today=stats["errors_today"],
        recipients_count=len(recipients),
    )
    await message.answer(
        f"✅ Переименовано (уведомлено {len(recipients)} получателей)\n\n{text}",
        reply_markup=funnel_card_kb(form_id, form.status == "active"),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:checkfields:"))
async def funnel_checkfields(callback: CallbackQuery, session: AsyncSession) -> None:
    import httpx
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Воронка не найдена.", show_alert=True)
        return
    await callback.answer()

    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        await callback.message.answer("⚠️ FACEBOOK_PAGE_ACCESS_TOKEN не задан в .env")
        return

    fb_form_id = form.fb_form_id
    if fb_form_id.startswith("gsheet_"):
        await callback.message.answer(
            f"ℹ️ Воронка <b>{escape(form.form_name)}</b> не привязана к Facebook форме "
            f"(используется только Google Sheet).",
            parse_mode="HTML",
        )
        return

    # --- Fetch form questions from FB Graph API ---
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"https://graph.facebook.com/{FACEBOOK_GRAPH_VERSION}/{fb_form_id}",
                params={"fields": "name,questions", "access_token": FACEBOOK_PAGE_ACCESS_TOKEN},
            )
            data = r.json()
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка запроса к FB API: {e}")
        return

    if "error" in data:
        err = data["error"]
        await callback.message.answer(
            f"⚠️ FB API ошибка:\n<code>{escape(err.get('message', str(err)))}</code>",
            parse_mode="HTML",
        )
        return

    questions = data.get("questions") or []
    form_name_fb = data.get("name", fb_form_id)

    # Map field keys to our fields
    _MAP = {
        "full_name": ["full_name", "name", "your_name", "first_name", "last_name"],
        "phone": ["phone_number", "phone", "mobile"],
        "email": ["email", "email_address"],
        "telegram": ["telegram", "tg", "telegram_username", "username"],
        "tag": ["utm_campaign", "utm_source", "utm_content", "utm_medium", "tag", "ref", "source", "campaign", "label"],
    }
    _LABELS = {
        "full_name": "Имя", "phone": "Телефон", "email": "Email",
        "telegram": "Telegram", "tag": "Тег",
    }

    found_keys = {str(q.get("key") or q.get("type") or "").strip().lower() for q in questions}
    found_labels = {str(q.get("label") or "").strip() for q in questions}

    lines = [f"<b>🔍 Форма:</b> {escape(form_name_fb)}", f"<b>FB Form ID:</b> <code>{fb_form_id}</code>", ""]
    if not questions:
        lines.append("⚠️ Поля формы не найдены (возможно нет прав или форма пуста).")
    else:
        lines.append("<b>Поля формы → наш маппинг:</b>")
        for q in questions:
            key = str(q.get("key") or q.get("type") or "").strip().lower()
            label = str(q.get("label") or key)
            mapped_to = None
            for field, aliases in _MAP.items():
                if key in aliases:
                    mapped_to = _LABELS[field]
                    break
            icon = "✅" if mapped_to else "—"
            arrow = f" → <b>{mapped_to}</b>" if mapped_to else ""
            lines.append(f"{icon} <code>{escape(label)}</code>{arrow}")

        lines.append("")
        # Check missing critical fields
        missing = []
        for field, aliases in _MAP.items():
            if field in ("tag",):
                continue
            matched = any(a in found_keys for a in aliases)
            if not matched:
                missing.append(_LABELS[field])
        if missing:
            lines.append(f"⚠️ Не захватывается: {', '.join(missing)}")
        else:
            lines.append("✅ Все ключевые поля захватываются.")

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅ Назад", callback_data=f"funnel:card:{form_id}")
    ]])
    await callback.message.edit_text("\n".join(lines), reply_markup=back_kb, parse_mode="HTML")


@router.callback_query(lambda c: c.data and (c.data.startswith("funnel:delete:") or c.data.startswith("funnel:archive:")))
async def funnel_archive(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Воронка не найдена.", show_alert=True)
        return
    from app.services.funnel_form_service import archive_form, list_forms
    await archive_form(session, form)
    forms = await list_forms(session)
    await callback.message.edit_text(
        f"<b>\U0001f4e6 Воронка архивирована: {escape(form.form_name)}</b>\n\n"
        f"Данные сохранены. Восстановить можно в разделе \"\U0001f4e6 Архив\".\n\nВсего воронок: {len(forms)}",
        reply_markup=funnel_list_kb(forms),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "funnel:archive_list")
async def funnel_archive_list(callback: CallbackQuery, session: AsyncSession) -> None:
    from app.services.funnel_form_service import list_archived_forms
    from app.bot.keyboards.funnel_kb import funnel_archive_list_kb
    forms = await list_archived_forms(session)
    if not forms:
        await callback.answer("Архив пуст.", show_alert=True)
        return
    await callback.message.edit_text(
        f"<b>\U0001f4e6 Архив воронок</b>\n\nВсего: {len(forms)}",
        reply_markup=funnel_archive_list_kb(forms),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:archived_card:"))
async def funnel_archived_card(callback: CallbackQuery, session: AsyncSession) -> None:
    from app.bot.keyboards.funnel_kb import funnel_archived_card_kb
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Воронка не найдена.", show_alert=True)
        return
    text = (
        f"<b>\U0001f4e6 {escape(form.form_name)}</b>\n\n"
        f"Статус: Архив\n"
        f"Тег: {escape(form.tag or '-')}\n"
        f"Создана: {form.created_at:%Y-%m-%d}"
    )
    await callback.message.edit_text(text, reply_markup=funnel_archived_card_kb(form_id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:restore:"))
async def funnel_restore(callback: CallbackQuery, session: AsyncSession) -> None:
    from app.services.funnel_form_service import restore_form, list_archived_forms, list_forms
    from app.bot.keyboards.funnel_kb import funnel_archive_list_kb
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Воронка не найдена.", show_alert=True)
        return
    await restore_form(session, form)
    archived = await list_archived_forms(session)
    if archived:
        await callback.message.edit_text(
            f"<b>\u267b\ufe0f Воронка восстановлена: {escape(form.form_name)}</b>\n\nВ архиве осталось: {len(archived)}",
            reply_markup=funnel_archive_list_kb(archived),
        )
    else:
        forms = await list_forms(session)
        await callback.message.edit_text(
            f"<b>\u267b\ufe0f Воронка восстановлена: {escape(form.form_name)}</b>\n\nАрхив пуст. Всего воронок: {len(forms)}",
            reply_markup=funnel_list_kb(forms),
        )
    await callback.answer("Восстановлено.")


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:delete_confirm:"))
async def funnel_delete_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("оронка не найдена.", show_alert=True)
        return
    from app.services.funnel_form_service import delete_form, list_forms
    name = form.form_name
    await delete_form(session, form)
    forms = await list_forms(session)
    await callback.message.edit_text(
        f"<b>✅ Воронка удалена: {escape(name)}</b>\n\nВсего воронок: {len(forms)}",
        reply_markup=funnel_list_kb(forms),
    )
    await callback.answer("Воронка удалена.", show_alert=True)


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:joinlink:"))
async def funnel_joinlink(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("оронка не найдена.", show_alert=True)
        return
    link = f"https://t.me/{BOT_USERNAME}?start=join_{form.id}_{form.join_code}"
    await callback.message.edit_text(
        f"<b>Ссылка для клиента</b>\n\n"
        f"Воронка: <b>{escape(form.form_name)}</b>\n"
        f"Тег: {escape(form.tag or '-')}\n\n"
        f"<code>{escape(link)}</code>\n\n"
        f"Отправьте клиенту. Сразу после Start ему придёт весь архив лидов.",
        reply_markup=funnel_card_kb(form_id, form.status == "active"),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:recipients:"))
async def funnel_recipients(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("оронка не найдена.", show_alert=True)
        return
    recipients = await list_recipients(session, form_id)
    await callback.message.edit_text(
        f"<b>Recipients: {escape(form.form_name)}</b>\n\nActive: {len(recipients)}",
        reply_markup=recipients_list_kb(recipients, form_id),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:delrecip:"))
async def funnel_del_recipient(callback: CallbackQuery, session: AsyncSession) -> None:
    recipient_id = _part_int(callback.data, 2)
    form_id = _part_int(callback.data, 3)
    if recipient_id is None or form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    await remove_recipient(session, recipient_id)
    form = await get_form_by_id(session, form_id)
    recipients = await list_recipients(session, form_id)
    await callback.message.edit_text(
        f"<b>Recipients: {escape(form.form_name if form else '-')}</b>\n\nActive: {len(recipients)}",
        reply_markup=recipients_list_kb(recipients, form_id),
    )
    await callback.answer("Recipient removed.")


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:leads:"))
async def funnel_leads(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    leads = await list_leads_by_funnel(session, form_id, limit=30)
    if not leads:
        await callback.answer("���� ���.", show_alert=True)
        return
    await callback.message.edit_text(
        f"<b>Последние лиды</b> ({len(leads)})",
        reply_markup=leads_list_kb(leads, back_cb=f"funnel:card:{form_id}"),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:sendold_menu:"))
async def funnel_sendold_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("оронка не найдена.", show_alert=True)
        return
    recipients = await list_recipients(session, form_id)
    if not recipients:
        await callback.answer("No active recipients.", show_alert=True)
        return
    leads = await list_leads_by_funnel(session, form_id)
    await callback.message.edit_text(
        f"<b>Send old leads</b>\n\n"
        f"Form: {escape(form.form_name)}\n"
        f"Leads: {len(leads)}\n"
        f"Recipients: {len(recipients)}",
        reply_markup=funnel_sendold_menu_kb(recipients, form_id),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:sendold_all:"))
async def funnel_sendold_all(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = _part_int(callback.data, 2)
    if form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    recipients = await list_recipients(session, form_id)
    leads = await list_leads_by_funnel(session, form_id)
    if not form or not recipients or not leads:
        await callback.answer("Nothing to send.", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(f"Sending {len(leads)} leads to {len(recipients)} recipients...")
    total_sent = total_skipped = 0
    for recipient in recipients:
        sent, skipped = await send_old_leads_to_recipient(session, callback.bot, recipient, leads, delay=0.15)
        total_sent += sent
        total_skipped += skipped
    await callback.message.edit_text(
        f"<b>Backfill finished</b>\n\nSent: {total_sent}\nSkipped/errors: {total_skipped}",
        reply_markup=funnel_card_kb(form_id, form.status == "active"),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:sendold_exec:"))
async def funnel_sendold_exec(callback: CallbackQuery, session: AsyncSession) -> None:
    recipient_id = _part_int(callback.data, 2)
    form_id = _part_int(callback.data, 3)
    if recipient_id is None or form_id is None:
        await callback.answer("Bad callback.", show_alert=True)
        return
    recipient = (await session.execute(
        select(ClientRecipient).where(ClientRecipient.id == recipient_id)
    )).scalar_one_or_none()
    form = await get_form_by_id(session, form_id)
    leads = await list_leads_by_funnel(session, form_id)
    if not recipient or not form or not leads:
        await callback.answer("Nothing to send.", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(f"Sending {len(leads)} leads...")
    sent, skipped = await send_old_leads_to_recipient(session, callback.bot, recipient, leads, delay=0.15)
    name = recipient.first_name or recipient.telegram_username or str(recipient.telegram_user_id)
    await callback.message.edit_text(
        f"<b>Backfill finished</b>\n\nRecipient: {escape(name)}\nSent: {sent}\nSkipped/errors: {skipped}",
        reply_markup=funnel_card_kb(form_id, form.status == "active"),
    )
