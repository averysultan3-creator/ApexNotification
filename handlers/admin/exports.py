import io
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin_kb import (
    ExportCb, MenuCb,
    export_section_kb, export_filter_kb, back_to_menu_kb,
    select_client_kb, select_offer_kb, SelectClientCb, SelectOfferCb,
)
from services.export_service import export_leads_csv, export_leads_xlsx
from services.client_service import get_clients_paginated
from services.offer_service import get_offers_paginated, get_offer_by_id
from services.client_service import get_client_by_id
from services.form_service import get_forms_paginated, get_form_by_id

logger = logging.getLogger(__name__)
router = Router()

_EXPORT_KEY = "export_filter"
_EXPORT_FMT = "export_fmt"


def _get_ef(data: dict) -> dict:
    return data.get(_EXPORT_KEY, {})


@router.callback_query(ExportCb.filter(F.action == "form"))
async def export_from_form(
    callback: CallbackQuery, callback_data: ExportCb, state: FSMContext, session: AsyncSession
) -> None:
    """Quick-start export pre-filtered to a specific form (from form_view_kb)."""
    try:
        form_id = int(callback_data.fmt)
    except (ValueError, TypeError):
        await callback.answer("❗ Неверный ID формы.", show_alert=True)
        return
    form = await get_form_by_id(session, form_id)
    for fmt in ("csv", "xlsx"):
        filter_state = {"form_id": form_id, "form_name": form.name if form else str(form_id)}
        await state.update_data(**{_EXPORT_FMT: "csv", _EXPORT_KEY: filter_state})
        break
    await callback.message.edit_text(
        f"📤 <b>Экспорт лидов формы</b>\n\nФорма: <b>{form.name if form else form_id}</b>\nВыберите формат:",
        reply_markup=export_filter_kb("csv", {"form_id": form_id, "form_name": form.name if form else str(form_id)}),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ExportCb.filter(F.action == "start"))
async def export_start(
    callback: CallbackQuery, callback_data: ExportCb, state: FSMContext
) -> None:
    fmt = callback_data.fmt
    await state.update_data(**{_EXPORT_FMT: fmt, _EXPORT_KEY: {}})
    data = await state.get_data()
    current = _get_ef(data)
    await callback.message.edit_text(
        f"📤 <b>Экспорт в {fmt.upper()}</b>\n\nНастройте фильтры:",
        reply_markup=export_filter_kb(fmt, current),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ExportCb.filter(F.action == "filter_client"))
async def export_filter_client(
    callback: CallbackQuery, callback_data: ExportCb, state: FSMContext, session: AsyncSession
) -> None:
    clients, _ = await get_clients_paginated(session, 0, 50)
    await state.update_data(export_select="client", export_select_fmt=callback_data.fmt)
    await callback.message.edit_text(
        "Выберите клиента (или пропустите для всех):",
        reply_markup=select_client_kb(clients),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ExportCb.filter(F.action == "filter_offer"))
async def export_filter_offer(
    callback: CallbackQuery, callback_data: ExportCb, state: FSMContext, session: AsyncSession
) -> None:
    offers, _ = await get_offers_paginated(session, 0, 50)
    await state.update_data(export_select="offer", export_select_fmt=callback_data.fmt)
    await callback.message.edit_text(
        "Выберите оффер:",
        reply_markup=select_offer_kb(offers),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ExportCb.filter(F.action == "filter_form"))
async def export_filter_form(
    callback: CallbackQuery, callback_data: ExportCb, state: FSMContext, session: AsyncSession
) -> None:
    from keyboards.admin_kb import select_form_for_stats_kb, StatsCb
    forms, _ = await get_forms_paginated(session, 0, 50)
    await state.update_data(export_select="form", export_select_fmt=callback_data.fmt)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    for f in forms:
        b.button(text=f.name, callback_data=ExportCb(action="pick_form", fmt=str(f.id)))
    b.button(text="❌ Отмена", callback_data=ExportCb(action="start", fmt=callback_data.fmt))
    b.adjust(1)
    await callback.message.edit_text(
        "Выберите форму:",
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ExportCb.filter(F.action == "pick_form"))
async def export_pick_form(
    callback: CallbackQuery, callback_data: ExportCb, state: FSMContext, session: AsyncSession
) -> None:
    form_id = int(callback_data.fmt)
    form = await get_form_by_id(session, form_id)
    data = await state.get_data()
    current = _get_ef(data)
    fmt = data.get(_EXPORT_FMT, "csv")
    current["form_id"] = form_id
    current["form_name"] = form.name if form else str(form_id)
    await state.update_data(**{_EXPORT_KEY: current})
    await callback.message.edit_text(
        f"📤 <b>Экспорт</b>",
        reply_markup=export_filter_kb(fmt, current),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(SelectClientCb.filter())
async def export_pick_client(
    callback: CallbackQuery, callback_data: SelectClientCb, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    if data.get("export_select") != "client":
        await callback.answer()
        return
    client = await get_client_by_id(session, callback_data.client_id)
    current = _get_ef(data)
    fmt = data.get(_EXPORT_FMT, "csv")
    current["client_id"] = callback_data.client_id
    current["client_name"] = client.name if client else str(callback_data.client_id)
    await state.update_data(**{_EXPORT_KEY: current})
    await callback.message.edit_text(
        "📤 <b>Экспорт</b>",
        reply_markup=export_filter_kb(fmt, current),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(SelectOfferCb.filter())
async def export_pick_offer(
    callback: CallbackQuery, callback_data: SelectOfferCb, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    if data.get("export_select") != "offer":
        await callback.answer()
        return
    offer = await get_offer_by_id(session, callback_data.offer_id)
    current = _get_ef(data)
    fmt = data.get(_EXPORT_FMT, "csv")
    current["offer_id"] = callback_data.offer_id
    current["offer_name"] = offer.name if offer else str(callback_data.offer_id)
    await state.update_data(**{_EXPORT_KEY: current})
    await callback.message.edit_text(
        "📤 <b>Экспорт</b>",
        reply_markup=export_filter_kb(fmt, current),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ExportCb.filter(F.action == "download"))
async def export_download(
    callback: CallbackQuery, callback_data: ExportCb, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    current = _get_ef(data)
    fmt = callback_data.fmt

    await callback.answer("⏳ Генерирую файл…")
    await callback.message.edit_text("⏳ <b>Экспорт…</b>", parse_mode="HTML")

    try:
        if fmt == "csv":
            file_bytes = await export_leads_csv(session, current or None)
            filename = "leads_export.csv"
            mime = "text/csv"
        else:
            file_bytes = await export_leads_xlsx(session, current or None)
            filename = "leads_export.xlsx"
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        doc = BufferedInputFile(file_bytes, filename=filename)
        await callback.message.answer_document(doc, caption=f"📤 Экспорт лидов ({fmt.upper()})")
        await callback.message.edit_text(
            "✅ <b>Файл отправлен!</b>",
            reply_markup=export_section_kb(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("Export error: %s", e)
        await callback.message.edit_text(
            "❗ Ошибка при генерации файла.",
            reply_markup=export_section_kb(),
            parse_mode="HTML",
        )
