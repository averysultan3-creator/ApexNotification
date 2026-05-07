"""
Admin handler: 📈 Conversions & Analytics dashboard.
All ConvCb + ConvExportCb callbacks are handled here.
"""
import logging
from typing import List

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from config import PAGE_SIZE
from keyboards.admin_kb import (
    ConvCb, ConvExportCb, MenuCb,
    conversions_menu_kb, conv_back_kb,
    conv_ref_actions_kb, conv_form_actions_kb, conv_export_kb,
    conv_select_form_for_dropoff_kb,
    conv_select_client_kb, conv_select_offer_kb, conv_select_form_kb,
    main_menu_kb,
)
from services.tracking_service import (
    get_funnel_stats,
    get_referral_conversion_stats,
    get_form_conversion_stats,
    get_offer_conversion_stats,
    get_client_conversion_stats,
    get_question_dropoff,
    get_top_sources,
    get_bad_sources,
)
from services.export_analytics_service import (
    export_funnel_by_source,
    export_dropoff_report,
    export_top_sources,
    export_bad_sources,
    export_full_analytics,
)
from services.client_service import get_clients_paginated, get_client_by_id
from services.offer_service import get_offers_paginated, get_offer_by_id
from services.form_service import get_forms_paginated, get_form_by_id
from services.referral_service import get_ref_by_id, get_refs_by_form

logger = logging.getLogger(__name__)
router = Router()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_funnel(stats: dict) -> str:
    lines = [
        f"📊 <b>Воронка:</b>",
        f"Стартов бота: <b>{stats['bot_starts']}</b>",
        f"Просмотров формы: <b>{stats['form_views']}</b>",
        f"Начали форму: <b>{stats['form_starts']}</b>",
        f"Завершили: <b>{stats['form_completions']}</b>",
        f"Лидов: <b>{stats['leads_created']}</b>",
        f"Дублей: <b>{stats['duplicates']}</b>",
        f"Qualified: <b>{stats['qualified']}</b>",
        f"Approved: <b>{stats['approved']}</b>",
        "",
        f"📉 <b>Конверсии:</b>",
        f"Start → Form start: <b>{stats['bot_to_form_start']}%</b>",
        f"Form start → Complete: <b>{stats['form_start_to_complete']}%</b>",
        f"Complete → Lead: <b>{stats['complete_to_lead']}%</b>",
        f"Lead → Qualified: <b>{stats['lead_to_qualified']}%</b>",
        f"Lead → Approved: <b>{stats['lead_to_approved']}%</b>",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Main conversions menu
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(ConvCb.filter(F.section == "menu"))
async def conv_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📈 <b>Конверсии и аналитика</b>\n\nВыберите раздел:",
        reply_markup=conversions_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Per-client
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(ConvCb.filter(F.section == "clients"))
async def conv_clients_list(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    clients, _ = await get_clients_paginated(session, 0, 50)
    if not clients:
        await callback.answer("Клиентов нет.", show_alert=True)
        return
    await callback.message.edit_text(
        "👥 <b>Конверсии по клиентам</b>\n\nВыберите клиента:",
        reply_markup=conv_select_client_kb(clients),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ConvCb.filter(F.section == "client"))
async def conv_client_view(
    callback: CallbackQuery, callback_data: ConvCb, session: AsyncSession
) -> None:
    client = await get_client_by_id(session, callback_data.id)
    if not client:
        await callback.answer("Клиент не найден.", show_alert=True)
        return
    stats = await get_client_conversion_stats(session, callback_data.id)
    text = (
        f"👤 <b>Клиент: {client.name}</b>\n\n"
        f"Лидов сегодня: <b>{stats['leads_today']}</b>\n"
        f"Лидов за 7 дней: <b>{stats['leads_7d']}</b>\n"
        f"Лидов за 30 дней: <b>{stats['leads_30d']}</b>\n\n"
        + _fmt_funnel(stats)
    )
    await callback.message.edit_text(text, reply_markup=conv_back_kb(), parse_mode="HTML")
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Per-offer
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(ConvCb.filter(F.section == "offers"))
async def conv_offers_list(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    offers, _ = await get_offers_paginated(session, 0, 50)
    if not offers:
        await callback.answer("Офферов нет.", show_alert=True)
        return
    await callback.message.edit_text(
        "📦 <b>Конверсии по офферам</b>\n\nВыберите оффер:",
        reply_markup=conv_select_offer_kb(offers),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ConvCb.filter(F.section == "offer"))
async def conv_offer_view(
    callback: CallbackQuery, callback_data: ConvCb, session: AsyncSession
) -> None:
    offer = await get_offer_by_id(session, callback_data.id)
    if not offer:
        await callback.answer("Оффер не найден.", show_alert=True)
        return
    stats = await get_offer_conversion_stats(session, callback_data.id)
    client_name = offer.client.name if offer.client else "—"
    text = (
        f"📦 <b>Оффер: {offer.name}</b>\n"
        f"Клиент: {client_name}\n\n"
        + _fmt_funnel(stats)
    )
    await callback.message.edit_text(text, reply_markup=conv_back_kb(), parse_mode="HTML")
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Per-form
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(ConvCb.filter(F.section == "forms"))
async def conv_forms_list(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    forms, _ = await get_forms_paginated(session, 0, 50)
    if not forms:
        await callback.answer("Форм нет.", show_alert=True)
        return
    await callback.message.edit_text(
        "📝 <b>Конверсии по формам</b>\n\nВыберите форму:",
        reply_markup=conv_select_form_kb(forms),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ConvCb.filter(F.section == "form"))
async def conv_form_view(
    callback: CallbackQuery, callback_data: ConvCb, session: AsyncSession
) -> None:
    form = await get_form_by_id(session, callback_data.id)
    if not form:
        await callback.answer("Форма не найдена.", show_alert=True)
        return
    stats = await get_form_conversion_stats(session, callback_data.id)
    client_name = form.client.name if form.client else "—"
    offer_name = form.offer.name if form.offer else "—"
    text = (
        f"📝 <b>Форма: {form.name}</b>\n"
        f"Клиент: {client_name} | Оффер: {offer_name}\n\n"
        + _fmt_funnel(stats)
    )
    await callback.message.edit_text(
        text,
        reply_markup=conv_form_actions_kb(callback_data.id),
        parse_mode="HTML",
    )
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Per-source (referral)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(ConvCb.filter(F.section == "refs"))
async def conv_refs_list(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    top = await get_top_sources(session, limit=50, order_by="leads_created")
    if not top:
        await callback.answer("Данных по источникам нет.", show_alert=True)
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    for r in top:
        b.button(
            text=f"🔗 {r['ref_name']} — {r['leads_created']} лидов",
            callback_data=ConvCb(section="ref", id=r["referral_source_id"]),
        )
    b.adjust(1)
    b.button(text="◀️ Назад", callback_data=ConvCb(section="menu"))
    await callback.message.edit_text(
        "🔗 <b>Конверсии по источникам</b>\n\nВыберите источник:",
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ConvCb.filter(F.section == "ref"))
async def conv_ref_view(
    callback: CallbackQuery, callback_data: ConvCb, session: AsyncSession
) -> None:
    ref = await get_ref_by_id(session, callback_data.id)
    if not ref:
        await callback.answer("Источник не найден.", show_alert=True)
        return
    stats = await get_referral_conversion_stats(session, callback_data.id)

    form = ref.form if ref.form else None
    client_name = form.client.name if form and form.client else "—"
    offer_name = form.offer.name if form and form.offer else "—"
    form_name = form.name if form else "—"
    form_id = form.id if form else 0

    last_lead = stats.get("last_lead_at")
    last_lead_str = last_lead.strftime("%d.%m.%Y %H:%M") if last_lead else "—"

    # UTM info line
    utm_parts = [
        p for p in [
            ref.traffic_source, ref.ad_account, ref.creative_name,
            ref.placement, ref.utm_geo,
        ] if p
    ]
    utm_line = " / ".join(utm_parts) if utm_parts else ""
    if ref.campaign_name:
        utm_line = f"{ref.campaign_name}" + (f" • {utm_line}" if utm_line else "")

    text = (
        f"🔗 <b>Источник: {ref.name}</b>\n"
        f"Код: <code>{ref.code}</code>\n"
        f"Клиент: {client_name}\n"
        f"Оффер: {offer_name}\n"
        f"Форма: {form_name}\n"
    )
    if utm_line:
        text += f"UTM: <i>{utm_line}</i>\n"
    text += "\n" + _fmt_funnel(stats)
    text += f"\n\n⚠️ Дубли: {stats['duplicates']}"
    text += f"\n⏱ Последний лид: {last_lead_str}"

    await callback.message.edit_text(
        text,
        reply_markup=conv_ref_actions_kb(callback_data.id, form_id),
        parse_mode="HTML",
    )
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Drop-off by question
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(ConvCb.filter(F.section == "dropoff"))
async def conv_dropoff(
    callback: CallbackQuery, callback_data: ConvCb, session: AsyncSession
) -> None:
    form_id = callback_data.id

    if not form_id:
        # Show form selection
        forms, _ = await get_forms_paginated(session, 0, 50)
        if not forms:
            await callback.answer("Форм нет.", show_alert=True)
            return
        await callback.message.edit_text(
            "❓ <b>Drop-off по вопросам</b>\n\nВыберите форму:",
            reply_markup=conv_select_form_for_dropoff_kb(forms),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена.", show_alert=True)
        return

    dropoff = await get_question_dropoff(session, form_id)
    if not dropoff:
        text = f"❓ <b>Drop-off: {form.name}</b>\n\n<i>Данных нет (нет событий question_viewed).</i>"
    else:
        lines = [f"❓ <b>Drop-off: {form.name}</b>\n"]
        for row in dropoff:
            q_text = row["question_text"][:40] + "…" if len(row["question_text"]) > 40 else row["question_text"]
            lines.append(
                f"Вопрос {row['step']}: <b>{q_text}</b>\n"
                f"  Просмотрели: {row['viewed']} | Ответили: {row['answered']}"
                f" ({row['answer_rate']}%) | Дропнули: {row['skipped']} ({row['dropoff_pct']}%)"
            )
        text = "\n".join(lines)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="📤 Экспорт drop-off", callback_data=ConvExportCb(what="dropoff", id=form_id))
    b.button(text="◀️ К конверсиям", callback_data=ConvCb(section="menu"))
    b.adjust(1)

    await callback.message.edit_text(text[:4096], reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Top sources
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(ConvCb.filter(F.section == "top"))
async def conv_top_sources(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    top = await get_top_sources(session, limit=15, order_by="approved")
    if not top:
        await callback.answer("Данных нет.", show_alert=True)
        return
    lines = ["🏆 <b>Топ источники по Approved</b>\n"]
    for i, r in enumerate(top, 1):
        lines.append(
            f"{i}. <b>{r['ref_name']}</b>\n"
            f"   Стартов: {r['bot_starts']} | Лидов: {r['leads_created']}"
            f" | Q: {r['qualified']} | ✅: {r['approved']}"
            f" ({r['approve_rate']}%)"
        )
    text = "\n".join(lines)[:4096]

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="📤 Экспорт", callback_data=ConvExportCb(what="top"))
    b.button(text="◀️ Назад", callback_data=ConvCb(section="menu"))
    b.adjust(1)

    await callback.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Bad sources
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(ConvCb.filter(F.section == "bad"))
async def conv_bad_sources(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    bad = await get_bad_sources(session, limit=15)
    if not bad:
        await callback.answer("Плохих источников нет (или данных мало).", show_alert=True)
        return
    lines = ["⚠️ <b>Плохие источники</b> (много стартов, мало approved)\n"]
    for i, r in enumerate(bad, 1):
        lines.append(
            f"{i}. <b>{r['ref_name']}</b>\n"
            f"   Стартов: {r['bot_starts']} | Лидов: {r['leads_created']}"
            f" | Completion: {r['completion_rate']}%"
            f" | Approve: {r['approve_rate']}%"
        )
    text = "\n".join(lines)[:4096]

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="📤 Экспорт", callback_data=ConvExportCb(what="bad"))
    b.button(text="◀️ Назад", callback_data=ConvCb(section="menu"))
    b.adjust(1)

    await callback.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Export menu + export actions
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(ConvCb.filter(F.section == "export"))
async def conv_export_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📤 <b>Экспорт аналитики</b>\n\nВыберите тип отчёта:",
        reply_markup=conv_export_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ConvExportCb.filter())
async def conv_export_do(
    callback: CallbackQuery, callback_data: ConvExportCb, session: AsyncSession, bot: Bot
) -> None:
    await callback.answer("⏳ Генерирую файл…")

    try:
        what = callback_data.what
        fid = callback_data.id

        if what == "funnel":
            data = await export_funnel_by_source(session)
            filename = "funnel_by_source.xlsx"
        elif what == "dropoff":
            if not fid:
                await callback.answer("Не выбрана форма.", show_alert=True)
                return
            data = await export_dropoff_report(session, fid)
            filename = f"dropoff_form_{fid}.xlsx"
        elif what == "top":
            data = await export_top_sources(session)
            filename = "top_sources.xlsx"
        elif what == "bad":
            data = await export_bad_sources(session)
            filename = "bad_sources.xlsx"
        elif what == "full":
            data = await export_full_analytics(session)
            filename = "full_analytics.xlsx"
        else:
            await callback.answer("Неизвестный тип.", show_alert=True)
            return

        file = BufferedInputFile(data, filename=filename)
        await bot.send_document(
            chat_id=callback.from_user.id,
            document=file,
            caption=f"📤 Аналитика: {filename}",
        )
    except Exception as exc:
        logger.error("Export analytics failed: %s", exc, exc_info=True)
        await bot.send_message(
            chat_id=callback.from_user.id,
            text="❗ Ошибка генерации отчёта. Попробуйте позже.",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Route ConvCb(section="client/offer/form") from stats selection keyboards
# They reuse select_*_for_stats_kb which emit StatsCb — so we need separate
# routing via ConvCb for clients/offers/forms selection in conv section.
# ─────────────────────────────────────────────────────────────────────────────

# The select_client_for_stats_kb emits StatsCb, so we need separate
# conv-specific keyboards or reuse them in conversions_router by checking state.
# To keep it clean: we use the existing StatsCb flow for the selection step,
# but add dedicated ConvCb handlers for the result display. The client/offer/form
# selection is delegated to the stats router's existing UI.
