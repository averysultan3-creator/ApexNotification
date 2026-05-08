from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.stats_kb import stats_menu_kb
from app.bot.keyboards.leads_kb import leads_list_kb
from app.services.stats_service import (
    dashboard_today, leads_by_client, leads_by_form, preland_stats_today
)
from app.services.lead_service import list_leads_errors, list_leads_today

router = Router(name="stats")

_back_kb = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="⬅️ Назад", callback_data="stats:menu")
]])


@router.callback_query(lambda c: c.data == "stats:menu")
async def stats_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    data = await dashboard_today(session)
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"📥 Лидов сегодня: {data['leads_today']}\n"
        f"✅ Доставлено: {data['delivered_today']}\n"
        f"⚠️ Ошибок: {data['delivery_errors_today']}\n\n"
        f"👁 Заходов: {data['preland_visits_today']}\n"
        f"👆 Кликов: {data['preland_clicks_today']}\n"
        f"📈 CTR: {data['preland_ctr_today']}%"
    )
    await callback.message.edit_text(text, reply_markup=stats_menu_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "stats:leads_today")
async def stats_leads_today(callback: CallbackQuery, session: AsyncSession) -> None:
    leads = await list_leads_today(session)
    if not leads:
        await callback.answer("Сегодня лидов нет.", show_alert=True)
        return
    await callback.message.edit_text(
        f"📥 Лиды сегодня ({len(leads)}):",
        reply_markup=leads_list_kb(leads, back_cb="stats:menu"),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "stats:by_form")
async def stats_by_form(callback: CallbackQuery, session: AsyncSession) -> None:
    rows = await leads_by_form(session)
    lines = ["📋 <b>Лиды по формам (всего):</b>\n"]
    for r in rows:
        lines.append(f"• {r['form']}: {r['count']}")
    await callback.message.edit_text("\n".join(lines) if rows else "Данных нет.", reply_markup=_back_kb)
    await callback.answer()


@router.callback_query(lambda c: c.data == "stats:by_client")
async def stats_by_client(callback: CallbackQuery, session: AsyncSession) -> None:
    rows = await leads_by_client(session)
    lines = ["👥 <b>Лиды по клиентам (всего):</b>\n"]
    for r in rows:
        lines.append(f"• {r['client']}: {r['count']}")
    await callback.message.edit_text("\n".join(lines) if rows else "Данных нет.", reply_markup=_back_kb)
    await callback.answer()


@router.callback_query(lambda c: c.data == "stats:prelands")
async def stats_prelands(callback: CallbackQuery, session: AsyncSession) -> None:
    rows = await preland_stats_today(session)
    lines = ["🌐 <b>Prelands сегодня:</b>\n"]
    for r in rows:
        lines.append(f"• {r['name']}: 👁{r['views']} 👆{r['clicks']} 📈{r['ctr']}%")
    await callback.message.edit_text("\n".join(lines) if rows else "Данных нет.", reply_markup=_back_kb)
    await callback.answer()


@router.callback_query(lambda c: c.data == "stats:errors")
async def stats_errors(callback: CallbackQuery, session: AsyncSession) -> None:
    leads = await list_leads_errors(session)
    if not leads:
        await callback.answer("Ошибок нет.", show_alert=True)
        return
    await callback.message.edit_text(
        f"⚠️ Ошибки доставки ({len(leads)}):",
        reply_markup=leads_list_kb(leads, back_cb="stats:menu"),
    )
    await callback.answer()
