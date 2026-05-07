"""
today_service.py — aggregates all data for the "📊 Сегодня" dashboard.

Queries:
  · site_events     — prelanding visits / CTA clicks / avg time on page
  · referral_source_stats_daily — bot funnel totals for today
  · leads           — status breakdown for today
  · referral_sources — best / worst source today
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.site_event import SiteEvent
from models.referral_source_stats_daily import ReferralSourceStatsDaily
from models.referral_source import ReferralSource
from models.lead import Lead


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _pct(part, total) -> str:
    if not total:
        return "0%"
    return f"{round(part / total * 100, 1)}%"


async def get_site_stats_today(session: AsyncSession, site_id: str) -> Dict[str, Any]:
    """
    Returns prelanding stats for today for a given site_id.
    Keys: visits, unique_visitors, cta_clicks, click_rate, avg_time_sec
    """
    today = _today()

    # visits
    visits_q = select(func.count()).where(
        and_(SiteEvent.site_id == site_id, SiteEvent.date == today, SiteEvent.event_type == "visit")
    )
    visits = (await session.execute(visits_q)).scalar() or 0

    # unique visitors (distinct session_id on visit events)
    uniq_q = select(func.count(SiteEvent.session_id.distinct())).where(
        and_(SiteEvent.site_id == site_id, SiteEvent.date == today, SiteEvent.event_type == "visit")
    )
    unique = (await session.execute(uniq_q)).scalar() or 0

    # cta clicks
    clicks_q = select(func.count()).where(
        and_(SiteEvent.site_id == site_id, SiteEvent.date == today, SiteEvent.event_type == "cta_click")
    )
    clicks = (await session.execute(clicks_q)).scalar() or 0

    # avg time on page (leave events)
    avg_q = select(func.avg(SiteEvent.time_spent)).where(
        and_(
            SiteEvent.site_id == site_id,
            SiteEvent.date == today,
            SiteEvent.event_type == "leave",
            SiteEvent.time_spent.isnot(None),
            SiteEvent.time_spent > 0,
        )
    )
    avg_time_raw = (await session.execute(avg_q)).scalar()
    avg_time = round(float(avg_time_raw)) if avg_time_raw else 0

    return {
        "visits": visits,
        "unique_visitors": unique,
        "cta_clicks": clicks,
        "click_rate": _pct(clicks, visits),
        "avg_time_sec": avg_time,
    }


async def get_all_site_ids_today(session: AsyncSession) -> List[str]:
    """Return distinct site_ids that sent at least one event today."""
    today = _today()
    q = select(SiteEvent.site_id.distinct()).where(
        and_(SiteEvent.date == today, SiteEvent.site_id.isnot(None))
    )
    rows = (await session.execute(q)).scalars().all()
    return [r for r in rows if r]


async def get_funnel_today(session: AsyncSession) -> Dict[str, Any]:
    """
    Returns aggregated bot funnel stats for today from daily stats table.
    Keys: bot_starts, form_views, form_starts, form_completions,
          leads_created, duplicates, completion_rate, lead_rate
    """
    today = _today()
    q = select(
        func.sum(ReferralSourceStatsDaily.bot_starts).label("bot_starts"),
        func.sum(ReferralSourceStatsDaily.form_views).label("form_views"),
        func.sum(ReferralSourceStatsDaily.form_starts).label("form_starts"),
        func.sum(ReferralSourceStatsDaily.form_completions).label("form_completions"),
        func.sum(ReferralSourceStatsDaily.leads_created).label("leads_created"),
        func.sum(ReferralSourceStatsDaily.duplicates).label("duplicates"),
    ).where(ReferralSourceStatsDaily.date == today)
    row = (await session.execute(q)).one()

    bot_starts = int(row.bot_starts or 0)
    form_starts = int(row.form_starts or 0)
    form_completions = int(row.form_completions or 0)
    leads_created = int(row.leads_created or 0)
    duplicates = int(row.duplicates or 0)

    return {
        "bot_starts": bot_starts,
        "form_views": int(row.form_views or 0),
        "form_starts": form_starts,
        "form_completions": form_completions,
        "leads_created": leads_created,
        "duplicates": duplicates,
        "completion_rate": _pct(form_completions, form_starts),
        "lead_rate": _pct(leads_created, form_completions),
    }


async def get_leads_by_status_today(session: AsyncSession) -> Dict[str, int]:
    """
    Returns counts per status for leads created today.
    """
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = today_start.replace(tzinfo=None)

    q = select(Lead.status, func.count(Lead.id)).where(
        Lead.created_at >= today_start
    ).group_by(Lead.status)
    rows = (await session.execute(q)).all()
    result = {row[0]: row[1] for row in rows}
    return result


async def get_best_worst_source_today(
    session: AsyncSession,
) -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Returns (best_source_dict, worst_source_dict) for today.
    Best = most approved today.
    Worst = most bot_starts but fewest leads (min 5 starts).
    """
    today = _today()
    q = select(
        ReferralSourceStatsDaily.referral_source_id,
        func.sum(ReferralSourceStatsDaily.bot_starts).label("starts"),
        func.sum(ReferralSourceStatsDaily.leads_created).label("leads"),
        func.sum(ReferralSourceStatsDaily.approved).label("approved"),
    ).where(
        and_(ReferralSourceStatsDaily.date == today, ReferralSourceStatsDaily.referral_source_id.isnot(None))
    ).group_by(ReferralSourceStatsDaily.referral_source_id)
    rows = (await session.execute(q)).all()

    if not rows:
        return None, None

    data = [
        {
            "ref_id": r.referral_source_id,
            "starts": int(r.starts or 0),
            "leads": int(r.leads or 0),
            "approved": int(r.approved or 0),
        }
        for r in rows
    ]

    # Enrich with names
    ref_ids = [d["ref_id"] for d in data]
    refs_q = select(ReferralSource.id, ReferralSource.name).where(ReferralSource.id.in_(ref_ids))
    ref_names = {row[0]: row[1] for row in (await session.execute(refs_q)).all()}
    for d in data:
        d["name"] = ref_names.get(d["ref_id"], f"ref_{d['ref_id']}")

    # Best: highest approved, fallback: highest leads
    best = max(data, key=lambda x: (x["approved"], x["leads"]))

    # Worst: most starts but fewest leads, only if >= 5 starts
    enough = [d for d in data if d["starts"] >= 5]
    worst = None
    if enough:
        worst = min(enough, key=lambda x: (x["leads"] / max(x["starts"], 1), -x["starts"]))

    return best, worst


async def get_today_dashboard(session: AsyncSession, site_id: str = "skyx_pl_1830") -> Dict[str, Any]:
    """Collect all data for the Сегодня screen in one call."""
    site = await get_site_stats_today(session, site_id)
    funnel = await get_funnel_today(session)
    statuses = await get_leads_by_status_today(session)
    best, worst = await get_best_worst_source_today(session)

    total_leads = sum(statuses.values())
    approved = statuses.get("approved", 0)

    return {
        "date": _today(),
        "site": site,
        "funnel": funnel,
        "statuses": statuses,
        "total_leads": total_leads,
        "approved": approved,
        "approve_rate": _pct(approved, total_leads),
        "best": best,
        "worst": worst,
    }
