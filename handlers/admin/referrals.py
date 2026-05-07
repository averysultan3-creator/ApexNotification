import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from config import BOT_USERNAME
from keyboards.admin_kb import (
    RefCb, RefEditCb, CancelCb, SelectSourceTypeCb, FormCb, ConfirmCb, StatsCb,
    refs_list_kb, ref_view_kb, ref_utm_kb, source_type_kb, cancel_kb, skip_cancel_kb,
    confirm_delete_kb, main_menu_kb,
)
from services.referral_service import (
    get_refs_by_form, get_ref_by_id, create_referral,
    update_ref_field, toggle_ref_status, delete_ref, build_start_link,
)
from services.form_service import get_form_by_id
from states.admin_states import CreateRefFSM, EditRefFSM
from utils.formatters import fmt_ref

logger = logging.getLogger(__name__)
router = Router()


# ── List refs for a form ──────────────────────────────────────────────────────

@router.callback_query(RefCb.filter(F.action == "list"))
async def refs_list(
    callback: CallbackQuery, callback_data: RefCb, session: AsyncSession
) -> None:
    form_id = callback_data.form_id
    refs = await get_refs_by_form(session, form_id)
    form = await get_form_by_id(session, form_id)
    form_name = form.name if form else "?"
    text = f"🔗 <b>Рефки формы «{form_name}»</b> (всего: {len(refs)})"
    await callback.message.edit_text(
        text, reply_markup=refs_list_kb(refs, form_id, callback_data.page), parse_mode="HTML"
    )
    await callback.answer()


# ── View ref ──────────────────────────────────────────────────────────────────

@router.callback_query(RefCb.filter(F.action == "view"))
async def ref_view(
    callback: CallbackQuery, callback_data: RefCb, session: AsyncSession
) -> None:
    ref = await get_ref_by_id(session, callback_data.id)
    if not ref:
        await callback.answer("Рефка не найдена", show_alert=True)
        return
    text = fmt_ref(ref, BOT_USERNAME)
    await callback.message.edit_text(
        text, reply_markup=ref_view_kb(ref), parse_mode="HTML"
    )
    await callback.answer()


# ── Create: wizard ────────────────────────────────────────────────────────────

@router.callback_query(RefCb.filter(F.action == "new"))
async def create_ref_start(
    callback: CallbackQuery, callback_data: RefCb, state: FSMContext
) -> None:
    await state.set_state(CreateRefFSM.waiting_name)
    await state.update_data(form_id=callback_data.form_id)
    await callback.message.edit_text(
        "➕ <b>Создание рефки</b>\n\nШаг 1/3: Введите <b>название источника</b> (напр. «FB - Adset 1»):",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateRefFSM.waiting_name)
async def create_ref_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("❗ Слишком короткое название.", reply_markup=cancel_kb())
        return
    await state.update_data(name=name)
    await state.set_state(CreateRefFSM.select_type)
    await message.answer(
        "Шаг 2/3: Выберите <b>тип источника</b>:",
        reply_markup=source_type_kb(),
        parse_mode="HTML",
    )


@router.callback_query(SelectSourceTypeCb.filter(), CreateRefFSM.select_type)
async def create_ref_source_type(
    callback: CallbackQuery, callback_data: SelectSourceTypeCb, state: FSMContext
) -> None:
    await state.update_data(source_type=callback_data.stype)
    await state.set_state(CreateRefFSM.waiting_notes)
    await callback.message.edit_text(
        "Шаг 3/3: Добавьте <b>заметки</b> об источнике (UTM, adset и т.д.) или нажмите «Пропустить»:",
        reply_markup=skip_cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateRefFSM.waiting_notes)
async def create_ref_notes(message: Message, state: FSMContext, session: AsyncSession) -> None:
    notes = (message.text or "").strip() or None
    data = await state.get_data()
    ref = await create_referral(
        session,
        form_id=data["form_id"],
        name=data["name"],
        source_type=data["source_type"],
        notes=notes,
    )
    await state.clear()
    link = build_start_link(ref.form_id, ref.code)
    text = (
        f"✅ Рефка <b>{ref.name}</b> создана!\n\n"
        f"{fmt_ref(ref, BOT_USERNAME)}\n\n"
        f"🔗 Ссылка для копирования:\n<code>{link}</code>"
    )
    await message.answer(text, reply_markup=ref_view_kb(ref), parse_mode="HTML")


# ── Edit name ─────────────────────────────────────────────────────────────────

@router.callback_query(RefCb.filter(F.action == "edit_name"))
async def ref_edit_name_start(
    callback: CallbackQuery, callback_data: RefCb, state: FSMContext
) -> None:
    await state.set_state(CreateRefFSM.confirming)
    await state.update_data(ref_id=callback_data.id, form_id=callback_data.form_id)
    await callback.message.edit_text(
        "✏️ Введите новое <b>название рефки</b>:",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateRefFSM.confirming)
async def ref_edit_name_save(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    new_name = (message.text or "").strip()
    if len(new_name) < 2:
        await message.answer("❗ Слишком короткое название.", reply_markup=cancel_kb())
        return
    ref = await update_ref_field(session, data["ref_id"], "name", new_name)
    await state.clear()
    if not ref:
        await message.answer("❗ Рефка не найдена.", reply_markup=main_menu_kb())
        return
    await message.answer(
        f"✅ Название изменено!\n\n{fmt_ref(ref, BOT_USERNAME)}",
        reply_markup=ref_view_kb(ref),
        parse_mode="HTML",
    )


# ── Toggle ────────────────────────────────────────────────────────────────────

@router.callback_query(RefCb.filter(F.action == "toggle"))
async def ref_toggle(
    callback: CallbackQuery, callback_data: RefCb, session: AsyncSession
) -> None:
    ref = await toggle_ref_status(session, callback_data.id)
    if not ref:
        await callback.answer("Рефка не найдена", show_alert=True)
        return
    label = "включена ✅" if ref.status == "active" else "выключена ⏸"
    await callback.answer(f"Рефка {label}", show_alert=True)
    await callback.message.edit_text(
        fmt_ref(ref, BOT_USERNAME), reply_markup=ref_view_kb(ref), parse_mode="HTML"
    )


# ── Delete ────────────────────────────────────────────────────────────────────

@router.callback_query(RefCb.filter(F.action == "del"))
async def ref_delete_confirm(
    callback: CallbackQuery, callback_data: RefCb, session: AsyncSession
) -> None:
    ref = await get_ref_by_id(session, callback_data.id)
    if not ref:
        await callback.answer("Рефка не найдена", show_alert=True)
        return
    await callback.message.edit_text(
        f"🗑 Удалить рефку <b>{ref.name}</b>?",
        reply_markup=confirm_delete_kb(f"ref_{ref.id}_{ref.form_id}"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ConfirmCb.filter(F.target.startswith("ref_")))
async def ref_delete_do(
    callback: CallbackQuery, callback_data: ConfirmCb, session: AsyncSession
) -> None:
    if callback_data.action != "yes":
        await callback.answer("Отменено.")
        await callback.message.edit_text("❌ Отменено.", reply_markup=main_menu_kb())
        return
    parts = callback_data.target.split("_")
    ref_id = int(parts[1])
    form_id = int(parts[2])
    ref = await get_ref_by_id(session, ref_id)
    name = ref.name if ref else "?"
    await delete_ref(session, ref_id)
    await callback.answer(f"✅ Рефка «{name}» удалена.")
    refs = await get_refs_by_form(session, form_id)
    await callback.message.edit_text(
        "🔗 <b>Рефки формы</b>",
        reply_markup=refs_list_kb(refs, form_id),
        parse_mode="HTML",
    )


# ── UTM edit menu ─────────────────────────────────────────────────────────────

_UTM_FIELD_LABELS = {
    "traffic_source": "Traffic source (напр. facebook)",
    "campaign_name": "Название кампании",
    "ad_account": "Ad account ID",
    "creative_name": "Creative name",
    "placement": "Placement",
    "utm_geo": "GEO",
}


@router.callback_query(RefCb.filter(F.action == "utm_menu"))
async def ref_utm_menu(
    callback: CallbackQuery, callback_data: RefCb, session: AsyncSession
) -> None:
    ref = await get_ref_by_id(session, callback_data.id)
    if not ref:
        await callback.answer("Рефка не найдена", show_alert=True)
        return
    lines = [f"🏷 <b>UTM-поля рефки «{ref.name}»</b>\n"]
    for field, label in _UTM_FIELD_LABELS.items():
        val = getattr(ref, field, None) or "<i>не задано</i>"
        lines.append(f"<b>{label}:</b> {val}")
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=ref_utm_kb(ref.id, ref.form_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(RefEditCb.filter())
async def ref_edit_utm_start(
    callback: CallbackQuery, callback_data: RefEditCb, state: FSMContext
) -> None:
    await state.set_state(EditRefFSM.waiting_value)
    await state.update_data(utm_field=callback_data.field, ref_id=callback_data.id)
    label = _UTM_FIELD_LABELS.get(callback_data.field, callback_data.field)
    await callback.message.edit_text(
        f"✏️ Введите значение для <b>{label}</b>\n(или нажмите «Пропустить» для очистки):",
        reply_markup=skip_cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(EditRefFSM.waiting_value)
async def ref_save_utm(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    field = data.get("utm_field")
    ref_id = data.get("ref_id")
    value = (message.text or "").strip() or None
    await state.clear()
    ref = await get_ref_by_id(session, ref_id)
    if ref and field:
        setattr(ref, field, value)
        await session.flush()
    if ref:
        await message.answer(
            fmt_ref(ref, BOT_USERNAME),
            reply_markup=ref_view_kb(ref),
            parse_mode="HTML",
        )
    else:
        await message.answer("❗ Рефка не найдена.", reply_markup=main_menu_kb())
