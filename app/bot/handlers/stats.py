from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.stats_kb import stats_menu_kb
from app.services.lead_service import list_leads_today
from app.services.stats_service import (
    delivery_errors,
    leads_by_client,
    leads_by_facebook_form,
    preland_visits_clicks_ctr,
)

router = Router(name="stats")


@router.callback_query(lambda c: c.data == "stats:menu")
async def stats_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text("📊 <b>Статистика</b>\n\nЧто смотреть?", reply_markup=stats_menu_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "stats:leads_today")
async def stats_leads_today(callback: CallbackQuery, session: AsyncSession) -> None:
    leads = await list_leads_today(session, limit=1_000)
    delivered = sum(1 for lead in leads if lead.delivered_telegram or lead.delivered_email or lead.delivered_sheet)
    await callback.message.edit_text(
        f"📥 <b>Лиды сегодня</b>\n\nВсего: {len(leads)}\nДоставлено: {delivered}",
        reply_markup=stats_menu_kb(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "stats:forms")
async def stats_forms(callback: CallbackQuery, session: AsyncSession) -> None:
    rows = await leads_by_facebook_form(session)
    text = "📋 <b>По FB формам</b>\n\n" + ("\n".join(f"{name}: {count}" for name, count in rows) or "Пока пусто.")
    await callback.message.edit_text(text, reply_markup=stats_menu_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "stats:clients")
async def stats_clients(callback: CallbackQuery, session: AsyncSession) -> None:
    rows = await leads_by_client(session)
    text = "👥 <b>По клиентам</b>\n\n" + ("\n".join(f"Client {client_id}: {count}" for client_id, count in rows) or "Пока пусто.")
    await callback.message.edit_text(text, reply_markup=stats_menu_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "stats:prelands")
async def stats_prelands(callback: CallbackQuery, session: AsyncSession) -> None:
    stats = await preland_visits_clicks_ctr(session)
    await callback.message.edit_text(
        "🌐 <b>Prelands</b>\n\n"
        f"Prelands: {stats['prelands']}\n"
        f"Visits: {stats['visits']}\n"
        f"Clicks: {stats['clicks']}\n"
        f"CTR: {stats['ctr']}%",
        reply_markup=stats_menu_kb(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "stats:errors")
async def stats_errors(callback: CallbackQuery, session: AsyncSession) -> None:
    logs = await delivery_errors(session)
    if not logs:
        text = "⚠️ <b>Ошибки доставки</b>\n\nОшибок нет."
    else:
        lines = ["⚠️ <b>Ошибки доставки</b>", ""]
        for log in logs:
            lines.append(f"Lead #{log.lead_id} / {log.channel} / {log.recipient}: {log.error_message or '-'}")
        text = "\n".join(lines)
    await callback.message.edit_text(text[:3500], reply_markup=stats_menu_kb())
    await callback.answer()
