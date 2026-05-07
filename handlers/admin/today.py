"""
handlers/admin/today.py — "📊 Сегодня" dashboard screen.

Shows:
  · prelanding stats (visits, CTA clicks, avg time)
  · bot funnel aggregates for today (starts, completions, leads)
  · leads by status today
  · best / worst source today
"""
import logging
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin_kb import TodayCb, MenuCb, today_kb
from services.today_service import get_today_dashboard, get_all_site_ids_today

logger = logging.getLogger(__name__)
router = Router()

# ── Site ID to show in the dashboard.  Change to match your prelanding. ──────
_DEFAULT_SITE_ID = "skyx_pl_1830"


def _fmt_time(seconds: int) -> str:
    if not seconds:
        return "—"
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def _fmt_today_text(data: dict) -> str:
    date_str = data["date"]
    site = data["site"]
    funnel = data["funnel"]
    statuses = data["statuses"]
    total_leads = data["total_leads"]
    approve_rate = data["approve_rate"]
    best = data["best"]
    worst = data["worst"]

    lines = [
        f"📊 <b>Сегодня — {date_str}</b>",
        "",
    ]

    # Prelanding stats
    visits = site["visits"]
    unique = site["unique_visitors"]
    clicks = site["cta_clicks"]
    click_rate = site["click_rate"]
    avg_time = _fmt_time(site["avg_time_sec"])

    if visits or clicks:
        lines += [
            "🌐 <b>Прелендинг SkyX PL 18-30:</b>",
            f"Визиты: <b>{visits:,}</b>  (уник: {unique:,})",
            f"Клики на CTA: <b>{clicks}</b> → {click_rate}",
            f"Среднее время: <b>{avg_time}</b>",
            "",
        ]

    # Bot funnel
    bot_starts = funnel["bot_starts"]
    form_starts = funnel["form_starts"]
    form_completions = funnel["form_completions"]
    leads_today_funnel = funnel["leads_created"]
    duplicates = funnel["duplicates"]
    completion_rate = funnel["completion_rate"]

    if bot_starts or leads_today_funnel:
        lines += [
            "🤖 <b>Воронка бота:</b>",
            f"Старты: <b>{bot_starts}</b>",
            f"Начали форму: <b>{form_starts}</b>",
            f"Завершили: <b>{form_completions}</b>  ({completion_rate})",
            f"Лиды: <b>{leads_today_funnel}</b>",
        ]
        if duplicates:
            lines.append(f"Дубли: {duplicates}")
        lines.append("")

    # Status breakdown
    new_leads = statuses.get("new", 0)
    contacted = statuses.get("contacted", 0)
    qualified = statuses.get("qualified", 0)
    approved = statuses.get("approved", 0)
    rejected = statuses.get("rejected", 0)

    if total_leads:
        lines += [
            "📈 <b>Результаты сегодня:</b>",
            f"🆕 Новых: <b>{new_leads}</b>",
        ]
        if contacted:
            lines.append(f"📞 Contacted: <b>{contacted}</b>")
        if qualified:
            lines.append(f"✅ Qualified: <b>{qualified}</b>")
        if approved:
            lines.append(f"🔥 Approved: <b>{approved}</b>")
        if rejected:
            lines.append(f"❌ Rejected: {rejected}")
        lines.append(f"Approve rate: <b>{approve_rate}</b>")
        lines.append("")

    # Best / worst source
    if best:
        b_rate = f"{round(best['approved'] / best['leads'] * 100)}%" if best.get('leads') else "0%"
        lines += [
            f"🏆 <b>Лучший источник:</b>",
            f"{best['name']} — {best['leads']} лидов / {best['approved']} approved / {b_rate}",
            "",
        ]

    if worst:
        w_rate = f"{round(worst['leads'] / worst['starts'] * 100)}%" if worst.get('starts') else "0%"
        lines += [
            f"⚠️ <b>Худший источник:</b>",
            f"{worst['name']} — {worst['starts']} стартов / {worst['leads']} лидов / {w_rate}",
        ]

    if not (visits or bot_starts or total_leads):
        lines.append("<i>Данных за сегодня пока нет.</i>")

    return "\n".join(lines)


async def _show_today(callback: CallbackQuery, session: AsyncSession) -> None:
    data = await get_today_dashboard(session, site_id=_DEFAULT_SITE_ID)
    text = _fmt_today_text(data)
    await callback.message.edit_text(text, reply_markup=today_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(MenuCb.filter(F.section == "today"))
async def today_open(callback: CallbackQuery, session: AsyncSession) -> None:
    await _show_today(callback, session)


@router.callback_query(TodayCb.filter(F.action == "refresh"))
async def today_refresh(callback: CallbackQuery, session: AsyncSession) -> None:
    await _show_today(callback, session)
