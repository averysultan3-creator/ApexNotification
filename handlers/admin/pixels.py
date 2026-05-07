"""
handlers/admin/pixels.py — 🎯 Pixel/events configuration.
"""
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin_kb import (
    PxCb, MenuCb, back_to_menu_kb,
    pixels_menu_kb, pixel_view_kb, pixel_type_kb, pixel_scope_kb, pixel_events_kb,
)
from models.pixel import PIXEL_TYPE_LABELS, PIXEL_EVENTS_ALL
from services.pixel_service import (
    get_all_pixels, get_pixel_by_id,
    create_pixel, toggle_pixel, delete_pixel, update_pixel_events,
)
from states.wizard_states import PixelWizardFSM

logger = logging.getLogger(__name__)
router = Router()

_HELP_TEXT = (
    "❔ <b>Что такое пиксель?</b>\n\n"
    "Пиксель помогает понять, какие источники дают не просто клики, "
    "а реальные заявки и approved-лиды.\n\n"
    "<b>События:</b>\n"
    "• <code>bot_started</code> — человек запустил бота\n"
    "• <code>form_viewed</code> — увидел форму\n"
    "• <code>form_started</code> — начал отвечать\n"
    "• <code>form_completed</code> — завершил форму\n"
    "• <code>lead_created</code> — оставил заявку\n"
    "• <code>approved</code> — заявка стала approved\n\n"
    "<b>Типы пикселей:</b>\n"
    "• Meta Pixel / Google Tag / TikTok Pixel — внешние\n"
    "• Telegram only — внутренний учёт событий в боте"
)


# ══════════════════════════════════════════════════════════════════════════════
# Main pixels screen
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(MenuCb.filter(F.section == "pixels"))
async def pixels_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    pixels = await get_all_pixels(session)

    by_type = {}
    for px in pixels:
        by_type.setdefault(px.pixel_type, []).append(px)

    lines = ["🎯 <b>Пиксели / события</b>\n"]
    lines.append("Здесь настраивается отслеживание конверсий.\n")

    type_status = {
        "meta": "не подключен",
        "google": "не подключен",
        "tiktok": "не подключен",
        "telegram": "не настроен",
    }
    for px in pixels:
        if px.is_active:
            type_status[px.pixel_type] = f"активен ({px.name})"
        elif px.pixel_type in type_status and type_status[px.pixel_type] in ("не подключен", "не настроен"):
            type_status[px.pixel_type] = f"отключён ({px.name})"

    lines.append(f"Meta Pixel:      <b>{type_status['meta']}</b>")
    lines.append(f"Google Tag:      <b>{type_status['google']}</b>")
    lines.append(f"TikTok Pixel:    <b>{type_status['tiktok']}</b>")
    lines.append(f"Telegram внутр.: <b>{type_status['telegram']}</b>")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=pixels_menu_kb(pixels),
        parse_mode="HTML",
    )
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
# View / toggle / delete single pixel
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(PxCb.filter(F.action == "view"))
async def pixel_view(
    callback: CallbackQuery, callback_data: PxCb, session: AsyncSession
) -> None:
    px = await get_pixel_by_id(session, callback_data.id)
    if not px:
        await callback.answer("Пиксель не найден", show_alert=True)
        return

    scope_labels = {
        "global": "Глобально",
        "client": "Клиент",
        "offer": "Оффер",
        "form": "Форма",
        "ref": "Источник",
    }
    events_fmt = "\n".join(f"  • {e}" for e in px.events_list) or "  (нет)"
    status = "✅ Активен" if px.is_active else "⏸ Отключён"

    text = (
        f"🎯 <b>{px.name}</b>\n\n"
        f"Тип:     {px.type_icon} <b>{px.type_label}</b>\n"
        f"Pixel ID: <code>{px.pixel_value or '—'}</code>\n"
        f"Область: <b>{scope_labels.get(px.scope_type, px.scope_type)}"
        f"{' #' + str(px.scope_id) if px.scope_id else ''}</b>\n"
        f"Статус:  {status}\n\n"
        f"События:\n{events_fmt}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=pixel_view_kb(px.id, px.is_active),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(PxCb.filter(F.action == "toggle"))
async def pixel_toggle(
    callback: CallbackQuery, callback_data: PxCb, session: AsyncSession
) -> None:
    px = await toggle_pixel(session, callback_data.id)
    if not px:
        await callback.answer("Пиксель не найден", show_alert=True)
        return
    await session.commit()
    state_str = "включён" if px.is_active else "отключён"
    await callback.answer(f"Пиксель {state_str}")
    # Refresh view
    await pixel_view(callback, callback_data, session)


@router.callback_query(PxCb.filter(F.action == "delete"))
async def pixel_delete(
    callback: CallbackQuery, callback_data: PxCb, session: AsyncSession
) -> None:
    await delete_pixel(session, callback_data.id)
    await session.commit()
    pixels = await get_all_pixels(session)
    await callback.message.edit_text(
        "🗑 Пиксель удалён.\n\n🎯 <b>Пиксели / события</b>",
        reply_markup=pixels_menu_kb(pixels),
        parse_mode="HTML",
    )
    await callback.answer("Удалено")


@router.callback_query(PxCb.filter(F.action == "events"))
async def pixel_events_menu(
    callback: CallbackQuery, callback_data: PxCb, session: AsyncSession, state: FSMContext
) -> None:
    px = await get_pixel_by_id(session, callback_data.id)
    if not px:
        await callback.answer("Не найден", show_alert=True)
        return
    await state.update_data({"_px_edit_id": callback_data.id, "_px_events": px.events_list})
    await callback.message.edit_text(
        f"📌 <b>События для {px.name}</b>\n\nВыбери активные события:",
        reply_markup=pixel_events_kb(px.events_list),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(PxCb.filter(F.action == "save_events"))
async def pixel_save_events(
    callback: CallbackQuery, callback_data: PxCb, session: AsyncSession, state: FSMContext
) -> None:
    data = await state.get_data()
    px_id = data.get("_px_edit_id")
    events = data.get("_px_events", [])

    if callback_data.id == 0:
        # "Save" button
        if px_id:
            await update_pixel_events(session, px_id, events)
            await session.commit()
        # Back to pixel view
        back_cb = PxCb(action="view", id=px_id or 0)
        await pixel_view(callback, back_cb, session)
        await callback.answer("Сохранено")
    else:
        # Toggle event by hash
        from models.pixel import PIXEL_EVENTS_ALL
        evt = next(
            (e for e in PIXEL_EVENTS_ALL if hash(e) & 0x7FFFFFFF == callback_data.id),
            None,
        )
        if evt:
            if evt in events:
                events.remove(evt)
            else:
                events.append(evt)
            await state.update_data({"_px_events": events})
        await callback.message.edit_reply_markup(reply_markup=pixel_events_kb(events))
        await callback.answer()


@router.callback_query(PxCb.filter(F.action == "help"))
async def pixel_help(callback: CallbackQuery) -> None:
    from keyboards.admin_kb import back_to_menu_kb, MenuCb
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="◀️ К пикселям", callback_data=MenuCb(section="pixels"))
    await callback.message.edit_text(
        _HELP_TEXT,
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
# Add pixel wizard
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(PxCb.filter(F.action == "add"))
async def pixel_add_start(
    callback: CallbackQuery, state: FSMContext
) -> None:
    await state.set_state(PixelWizardFSM.select_type)
    await callback.message.edit_text(
        "🎯 <b>Добавить пиксель</b>\n\nВыбери тип:",
        reply_markup=pixel_type_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


_TYPE_MAP = {1: "meta", 2: "google", 3: "tiktok", 4: "telegram"}


@router.callback_query(PxCb.filter(F.action == "type"), PixelWizardFSM.select_type)
async def pixel_add_type(
    callback: CallbackQuery, callback_data: PxCb, state: FSMContext
) -> None:
    px_type = _TYPE_MAP.get(callback_data.id, "telegram")
    await state.update_data({"_new_px_type": px_type, "_new_px_events": list(PIXEL_EVENTS_ALL[:4])})

    if px_type == "telegram":
        await state.update_data({"_new_px_val": ""})
        await state.set_state(PixelWizardFSM.enter_name)
        await callback.message.edit_text(
            "✈️ <b>Telegram Tracking</b>\n\nВведи название для этого конфига:",
            parse_mode="HTML",
        )
    else:
        await state.set_state(PixelWizardFSM.enter_pixel_id)
        label = PIXEL_TYPE_LABELS.get(px_type, px_type)
        await callback.message.edit_text(
            f"🎯 <b>{label}</b>\n\nВведи Pixel ID:\n<i>Например: 123456789012345</i>",
            parse_mode="HTML",
        )
    await callback.answer()


@router.message(PixelWizardFSM.enter_pixel_id)
async def pixel_add_id(message: Message, state: FSMContext) -> None:
    px_val = message.text.strip()
    if not px_val:
        await message.answer("❌ ID не может быть пустым:")
        return
    await state.update_data({"_new_px_val": px_val})
    await state.set_state(PixelWizardFSM.enter_name)
    await message.answer(
        f"✅ ID: <code>{px_val}</code>\n\nВведи название пикселя:\n"
        f"<i>Например: Meta Pixel Finance UA</i>",
        parse_mode="HTML",
    )


@router.message(PixelWizardFSM.enter_name)
async def pixel_add_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("❌ Название не может быть пустым:")
        return
    await state.update_data({"_new_px_name": name})
    await state.set_state(PixelWizardFSM.select_scope_type)
    await message.answer(
        f"Пиксель: <b>{name}</b>\n\nК чему привязать?",
        reply_markup=pixel_scope_kb(),
        parse_mode="HTML",
    )


_SCOPE_MAP = {0: "global", 1: "client", 2: "offer", 3: "form", 4: "ref"}


@router.callback_query(PxCb.filter(F.action == "scope"), PixelWizardFSM.select_scope_type)
async def pixel_add_scope(
    callback: CallbackQuery, callback_data: PxCb, state: FSMContext, session: AsyncSession
) -> None:
    scope = _SCOPE_MAP.get(callback_data.id, "global")
    await state.update_data({"_new_px_scope": scope})

    data = await state.get_data()
    px_type = data["_new_px_type"]
    px_val = data.get("_new_px_val", "")
    px_name = data["_new_px_name"]
    events_list = data.get("_new_px_events", [])

    px = await create_pixel(
        session,
        name=px_name,
        pixel_type=px_type,
        pixel_value=px_val,
        scope_type=scope,
        events=",".join(events_list),
    )
    await session.commit()
    await state.clear()

    from keyboards.admin_kb import MenuCb
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="◀️ К пикселям", callback_data=MenuCb(section="pixels"))

    await callback.message.edit_text(
        f"✅ <b>Пиксель подключён</b>\n\n"
        f"Тип:   {px.type_icon} <b>{px.type_label}</b>\n"
        f"ID:    <code>{px.pixel_value or '—'}</code>\n"
        f"Область: <b>{scope}</b>\n\n"
        f"События:\n" + "\n".join(f"  • {e}" for e in events_list),
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()
