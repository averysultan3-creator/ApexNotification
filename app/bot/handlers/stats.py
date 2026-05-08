from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.stats_kb import stats_menu_kb
from app.services.lead_service import list_leads_today
from app.services.stats_service import (
    delivery_errors,
    leads_by_client,
    leads_by_facebook_form,
    leads_stats_by_day,
    preland_stats_by_day,
    preland_stats_by_hour,
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


@router.callback_query(lambda c: c.data == "stats:leads_days")
async def stats_leads_days(callback: CallbackQuery, session: AsyncSession) -> None:
    rows = await leads_stats_by_day(session, days=7)
    if not rows:
        await callback.message.edit_text("📅 Лидов за 7 дней нет.", reply_markup=stats_menu_kb())
        await callback.answer()
        return
    lines = ["📅 <b>Лиды по дням (7д)</b>\n"]
    for r in rows:
        bar = "█" * min(r["leads"], 20) if r["leads"] else "·"
        lines.append(f"<code>{r['day']}</code>  {bar}  {r['leads']}")
    await callback.message.edit_text("\n".join(lines), reply_markup=stats_menu_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data in ("stats:pl_days", "stats:pl_days_7"))
async def stats_pl_days(callback: CallbackQuery, session: AsyncSession) -> None:
    days = 7 if callback.data == "stats:pl_days_7" else 3
    rows = await preland_stats_by_day(session, days=days)
    if not rows:
        await callback.message.edit_text(f"📅 Нет данных за {days}д.", reply_markup=stats_menu_kb())
        await callback.answer()
        return
    lines = [f"📅 <b>Prelands по дням ({days}д)</b>\n"]
    for r in rows:
        bar_v = "▓" * min(r["visits"], 15)
        bar_c = "░" * min(r["clicks"], 15)
        lines.append(
            f"<code>{r['day']}</code>\n"
            f"  👁 {r['visits']} {bar_v}\n"
            f"  👆 {r['clicks']} {bar_c}  CTR {r['ctr']}%"
        )
    await callback.message.edit_text("\n".join(lines)[:3800], reply_markup=stats_menu_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "stats:pl_hours")
async def stats_pl_hours(callback: CallbackQuery, session: AsyncSession) -> None:
    rows = await preland_stats_by_hour(session)
    if not rows:
        await callback.message.edit_text("🕐 Сегодня данных нет.", reply_markup=stats_menu_kb())
        await callback.answer()
        return
    lines = ["🕐 <b>Prelands по часам (сегодня, UTC)</b>\n"]
    for r in rows:
        bar = "█" * min(r["visits"], 12) if r["visits"] else "·"
        lines.append(
            f"<code>{r['hour']}</code>  👁{r['visits']} 👆{r['clicks']}  {bar}  CTR {r['ctr']}%"
        )
    await callback.message.edit_text("\n".join(lines)[:3800], reply_markup=stats_menu_kb())
    await callback.answer()
