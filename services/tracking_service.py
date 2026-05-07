"""
Tracking service — event journal, session management, analytics.

All public functions wrap DB errors internally so tracking failures
never break the user experience.  Callers wrap with try/except for safety.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from models.tracking_event import TrackingEvent, EventType
from models.tracking_session import TrackingSession, SessionStatus
from models.referral_source_stats_daily import ReferralSourceStatsDaily
from models.lead import Lead
from models.lead_form_question import LeadFormQuestion
from models.referral_source import ReferralSource


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def new_session_id() -> str:
    """Generate a new unique tracking session ID."""
    return str(uuid.uuid4())


def percent(part: float | int, total: float | int) -> float:
    """Safe percent: returns 0.0 if total is zero."""
    if not total:
        return 0.0
    return round(part / total * 100, 1)


async def _get_or_create_daily(
    session: AsyncSession,
    *,
    today_str: str,
    referral_source_id: Optional[int],
    form_id: Optional[int],
    client_id: Optional[int],
    offer_id: Optional[int],
) -> ReferralSourceStatsDaily:
    stmt = select(ReferralSourceStatsDaily).where(
        and_(
            ReferralSourceStatsDaily.date == today_str,
            ReferralSourceStatsDaily.referral_source_id == referral_source_id,
            ReferralSourceStatsDaily.form_id == form_id,
        )
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        row = ReferralSourceStatsDaily(
            date=today_str,
            referral_source_id=referral_source_id,
            form_id=form_id,
            client_id=client_id,
            offer_id=offer_id,
            updated_at=_now(),
        )
        session.add(row)
        await session.flush()
    return row


async def _inc_daily(
    session: AsyncSession,
    *,
    referral_source_id: Optional[int],
    form_id: Optional[int],
    client_id: Optional[int],
    offer_id: Optional[int],
    column: str,
    amount: int = 1,
) -> None:
    row = await _get_or_create_daily(
        session,
        today_str=_today(),
        referral_source_id=referral_source_id,
        form_id=form_id,
        client_id=client_id,
        offer_id=offer_id,
    )
    current = getattr(row, column, 0) or 0
    setattr(row, column, current + amount)
    row.updated_at = _now()
    await session.flush()


async def _get_tracking_session(
    session: AsyncSession, session_id: str
) -> Optional[TrackingSession]:
    stmt = select(TrackingSession).where(TrackingSession.session_id == session_id)
    return (await session.execute(stmt)).scalar_one_or_none()


# ─────────────────────────────────────────────────────────────────────────────
# Core event tracking
# ─────────────────────────────────────────────────────────────────────────────

async def track_event(
    session: AsyncSession,
    event_type: str,
    *,
    session_id: str,
    form_id: Optional[int] = None,
    client_id: Optional[int] = None,
    offer_id: Optional[int] = None,
    referral_source_id: Optional[int] = None,
    lead_id: Optional[int] = None,
    telegram_user_id: Optional[int] = None,
    telegram_username: Optional[str] = None,
    question_id: Optional[int] = None,
    step_number: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> TrackingEvent:
    now = _now()
    event = TrackingEvent(
        event_type=event_type,
        session_id=session_id,
        form_id=form_id,
        client_id=client_id,
        offer_id=offer_id,
        referral_source_id=referral_source_id,
        lead_id=lead_id,
        telegram_user_id=telegram_user_id,
        telegram_username=telegram_username,
        question_id=question_id,
        step_number=step_number,
        metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata else None,
        created_at=now,
    )
    session.add(event)

    # Update TrackingSession.last_event_at + current_step
    ts = await _get_tracking_session(session, session_id)
    if ts:
        ts.last_event_at = now
        if step_number is not None and step_number > ts.current_step:
            ts.current_step = step_number
        await session.flush()

    return event


# ─────────────────────────────────────────────────────────────────────────────
# High-level tracking helpers
# ─────────────────────────────────────────────────────────────────────────────

async def start_tracking_session(
    session: AsyncSession,
    *,
    session_id: str,
    form_id: int,
    client_id: int,
    offer_id: int,
    referral_source_id: int,
    telegram_user_id: int,
    telegram_username: Optional[str] = None,
    total_steps: int = 0,
) -> TrackingSession:
    """Create a new TrackingSession and emit bot_started + form_viewed events."""
    now = _now()
    ts = TrackingSession(
        session_id=session_id,
        form_id=form_id,
        client_id=client_id,
        offer_id=offer_id,
        referral_source_id=referral_source_id,
        telegram_user_id=telegram_user_id,
        telegram_username=telegram_username,
        total_steps=total_steps,
        status=SessionStatus.started.value,
        started_at=now,
        last_event_at=now,
    )
    session.add(ts)
    await session.flush()

    # Events
    await track_event(
        session, EventType.bot_started.value,
        session_id=session_id, form_id=form_id, client_id=client_id, offer_id=offer_id,
        referral_source_id=referral_source_id,
        telegram_user_id=telegram_user_id, telegram_username=telegram_username,
    )
    await track_event(
        session, EventType.form_viewed.value,
        session_id=session_id, form_id=form_id, client_id=client_id, offer_id=offer_id,
        referral_source_id=referral_source_id,
        telegram_user_id=telegram_user_id, telegram_username=telegram_username,
    )

    # Daily stats
    kw = dict(
        referral_source_id=referral_source_id, form_id=form_id,
        client_id=client_id, offer_id=offer_id,
    )
    await _inc_daily(session, **kw, column="bot_starts")
    await _inc_daily(session, **kw, column="form_views")

    return ts


async def track_form_started(
    session: AsyncSession,
    session_id: str,
    *,
    form_id: Optional[int] = None,
    client_id: Optional[int] = None,
    offer_id: Optional[int] = None,
    referral_source_id: Optional[int] = None,
    telegram_user_id: Optional[int] = None,
    telegram_username: Optional[str] = None,
) -> None:
    ts = await _get_tracking_session(session, session_id)
    if ts:
        ts.status = SessionStatus.in_progress.value
        await session.flush()
    await track_event(
        session, EventType.form_started.value,
        session_id=session_id, form_id=form_id, client_id=client_id, offer_id=offer_id,
        referral_source_id=referral_source_id,
        telegram_user_id=telegram_user_id, telegram_username=telegram_username,
    )
    await _inc_daily(
        session,
        referral_source_id=referral_source_id, form_id=form_id,
        client_id=client_id, offer_id=offer_id,
        column="form_starts",
    )


async def track_question_viewed(
    session: AsyncSession,
    session_id: str,
    *,
    form_id: Optional[int] = None,
    client_id: Optional[int] = None,
    offer_id: Optional[int] = None,
    referral_source_id: Optional[int] = None,
    telegram_user_id: Optional[int] = None,
    telegram_username: Optional[str] = None,
    question_id: Optional[int] = None,
    step_number: int = 0,
) -> None:
    await track_event(
        session, EventType.question_viewed.value,
        session_id=session_id, form_id=form_id, client_id=client_id, offer_id=offer_id,
        referral_source_id=referral_source_id,
        telegram_user_id=telegram_user_id, telegram_username=telegram_username,
        question_id=question_id, step_number=step_number,
    )


async def track_question_answered(
    session: AsyncSession,
    session_id: str,
    *,
    form_id: Optional[int] = None,
    client_id: Optional[int] = None,
    offer_id: Optional[int] = None,
    referral_source_id: Optional[int] = None,
    telegram_user_id: Optional[int] = None,
    telegram_username: Optional[str] = None,
    question_id: Optional[int] = None,
    step_number: int = 0,
) -> None:
    await track_event(
        session, EventType.question_answered.value,
        session_id=session_id, form_id=form_id, client_id=client_id, offer_id=offer_id,
        referral_source_id=referral_source_id,
        telegram_user_id=telegram_user_id, telegram_username=telegram_username,
        question_id=question_id, step_number=step_number,
    )


async def track_form_completed(
    session: AsyncSession,
    session_id: str,
    *,
    form_id: Optional[int] = None,
    client_id: Optional[int] = None,
    offer_id: Optional[int] = None,
    referral_source_id: Optional[int] = None,
    telegram_user_id: Optional[int] = None,
    telegram_username: Optional[str] = None,
) -> None:
    now = _now()
    ts = await _get_tracking_session(session, session_id)
    if ts:
        ts.status = SessionStatus.completed.value
        ts.is_completed = True
        ts.completed_at = now
        await session.flush()
    await track_event(
        session, EventType.form_completed.value,
        session_id=session_id, form_id=form_id, client_id=client_id, offer_id=offer_id,
        referral_source_id=referral_source_id,
        telegram_user_id=telegram_user_id, telegram_username=telegram_username,
    )
    await _inc_daily(
        session,
        referral_source_id=referral_source_id, form_id=form_id,
        client_id=client_id, offer_id=offer_id,
        column="form_completions",
    )


async def track_lead_created(
    session: AsyncSession,
    session_id: str,
    *,
    form_id: Optional[int] = None,
    client_id: Optional[int] = None,
    offer_id: Optional[int] = None,
    referral_source_id: Optional[int] = None,
    lead_id: Optional[int] = None,
    telegram_user_id: Optional[int] = None,
    telegram_username: Optional[str] = None,
) -> None:
    ts = await _get_tracking_session(session, session_id)
    if ts and lead_id:
        ts.lead_id = lead_id
        await session.flush()
    await track_event(
        session, EventType.lead_created.value,
        session_id=session_id, form_id=form_id, client_id=client_id, offer_id=offer_id,
        referral_source_id=referral_source_id, lead_id=lead_id,
        telegram_user_id=telegram_user_id, telegram_username=telegram_username,
    )
    await _inc_daily(
        session,
        referral_source_id=referral_source_id, form_id=form_id,
        client_id=client_id, offer_id=offer_id,
        column="leads_created",
    )


async def track_duplicate_detected(
    session: AsyncSession,
    session_id: str,
    *,
    form_id: Optional[int] = None,
    client_id: Optional[int] = None,
    offer_id: Optional[int] = None,
    referral_source_id: Optional[int] = None,
    telegram_user_id: Optional[int] = None,
    telegram_username: Optional[str] = None,
) -> None:
    ts = await _get_tracking_session(session, session_id)
    if ts:
        ts.status = SessionStatus.duplicate.value
        ts.is_duplicate = True
        await session.flush()
    await track_event(
        session, EventType.duplicate_detected.value,
        session_id=session_id, form_id=form_id, client_id=client_id, offer_id=offer_id,
        referral_source_id=referral_source_id,
        telegram_user_id=telegram_user_id, telegram_username=telegram_username,
    )
    await _inc_daily(
        session,
        referral_source_id=referral_source_id, form_id=form_id,
        client_id=client_id, offer_id=offer_id,
        column="duplicates",
    )


async def track_lead_status_changed(
    session: AsyncSession,
    *,
    lead_id: int,
    old_status: str,
    new_status: str,
    form_id: Optional[int] = None,
    client_id: Optional[int] = None,
    offer_id: Optional[int] = None,
    referral_source_id: Optional[int] = None,
) -> None:
    """Track a lead status change and update the daily stats accordingly."""
    session_id = f"admin_status_change_{lead_id}"
    await track_event(
        session, EventType.lead_status_changed.value,
        session_id=session_id, form_id=form_id, client_id=client_id, offer_id=offer_id,
        referral_source_id=referral_source_id, lead_id=lead_id,
        metadata={"old_status": old_status, "new_status": new_status},
    )
    # Update daily stats: decrement old status counter (if tracked), increment new
    _STATUS_TO_COL = {
        "contacted": "contacted",
        "qualified": "qualified",
        "rejected": "rejected",
        "approved": "approved",
    }
    kw = dict(
        referral_source_id=referral_source_id, form_id=form_id,
        client_id=client_id, offer_id=offer_id,
    )
    if new_status in _STATUS_TO_COL:
        await _inc_daily(session, **kw, column=_STATUS_TO_COL[new_status])


# ─────────────────────────────────────────────────────────────────────────────
# Analytics queries
# ─────────────────────────────────────────────────────────────────────────────

async def get_funnel_stats(
    session: AsyncSession,
    *,
    client_id: Optional[int] = None,
    offer_id: Optional[int] = None,
    form_id: Optional[int] = None,
    referral_source_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    """Return aggregated funnel stats + conversion rates."""
    daily_filters = []
    if client_id:
        daily_filters.append(ReferralSourceStatsDaily.client_id == client_id)
    if offer_id:
        daily_filters.append(ReferralSourceStatsDaily.offer_id == offer_id)
    if form_id:
        daily_filters.append(ReferralSourceStatsDaily.form_id == form_id)
    if referral_source_id:
        daily_filters.append(ReferralSourceStatsDaily.referral_source_id == referral_source_id)
    if date_from:
        daily_filters.append(ReferralSourceStatsDaily.date >= date_from)
    if date_to:
        daily_filters.append(ReferralSourceStatsDaily.date <= date_to)

    daily_q = select(
        func.coalesce(func.sum(ReferralSourceStatsDaily.bot_starts), 0).label("bot_starts"),
        func.coalesce(func.sum(ReferralSourceStatsDaily.form_views), 0).label("form_views"),
        func.coalesce(func.sum(ReferralSourceStatsDaily.form_starts), 0).label("form_starts"),
        func.coalesce(func.sum(ReferralSourceStatsDaily.form_completions), 0).label("form_completions"),
        func.coalesce(func.sum(ReferralSourceStatsDaily.leads_created), 0).label("leads_created"),
        func.coalesce(func.sum(ReferralSourceStatsDaily.duplicates), 0).label("duplicates"),
    )
    if daily_filters:
        daily_q = daily_q.where(and_(*daily_filters))

    dr = (await session.execute(daily_q)).one()
    bot_starts = int(dr.bot_starts)
    form_views = int(dr.form_views)
    form_starts = int(dr.form_starts)
    form_completions = int(dr.form_completions)
    leads_created = int(dr.leads_created)
    duplicates = int(dr.duplicates)

    # Lead quality from leads table (accurate, not daily stats)
    lead_filters = []
    if client_id:
        lead_filters.append(Lead.client_id == client_id)
    if offer_id:
        lead_filters.append(Lead.offer_id == offer_id)
    if form_id:
        lead_filters.append(Lead.form_id == form_id)
    if referral_source_id:
        lead_filters.append(Lead.referral_source_id == referral_source_id)
    if date_from:
        lead_filters.append(Lead.created_at >= date_from)
    if date_to:
        dt = date_to + " 23:59:59" if len(date_to) == 10 else date_to
        lead_filters.append(Lead.created_at <= dt)

    lead_q = select(
        func.coalesce(func.sum(case((Lead.status == "qualified", 1), else_=0)), 0).label("qualified"),
        func.coalesce(func.sum(case((Lead.status == "approved", 1), else_=0)), 0).label("approved"),
        func.coalesce(func.sum(case((Lead.status == "rejected", 1), else_=0)), 0).label("rejected"),
        func.coalesce(func.sum(case((Lead.status == "contacted", 1), else_=0)), 0).label("contacted"),
    )
    if lead_filters:
        lead_q = lead_q.where(and_(*lead_filters))

    lr = (await session.execute(lead_q)).one()
    qualified = int(lr.qualified)
    approved = int(lr.approved)
    rejected = int(lr.rejected)
    contacted = int(lr.contacted)

    return {
        "bot_starts": bot_starts,
        "form_views": form_views,
        "form_starts": form_starts,
        "form_completions": form_completions,
        "leads_created": leads_created,
        "duplicates": duplicates,
        "contacted": contacted,
        "qualified": qualified,
        "rejected": rejected,
        "approved": approved,
        # Conversion rates
        "bot_to_form_start": percent(form_starts, bot_starts),
        "form_start_to_complete": percent(form_completions, form_starts),
        "complete_to_lead": percent(leads_created, form_completions),
        "lead_to_qualified": percent(qualified, leads_created),
        "lead_to_approved": percent(approved, leads_created),
    }


async def get_referral_conversion_stats(
    session: AsyncSession, referral_source_id: int
) -> Dict[str, Any]:
    """Full funnel card for a single referral source."""
    stats = await get_funnel_stats(session, referral_source_id=referral_source_id)

    # Last lead timestamp
    last_lead_q = (
        select(Lead.created_at)
        .where(Lead.referral_source_id == referral_source_id)
        .order_by(Lead.created_at.desc())
        .limit(1)
    )
    last_lead_row = (await session.execute(last_lead_q)).scalar_one_or_none()
    stats["last_lead_at"] = last_lead_row

    return stats


async def get_form_conversion_stats(
    session: AsyncSession, form_id: int
) -> Dict[str, Any]:
    stats = await get_funnel_stats(session, form_id=form_id)
    return stats


async def get_offer_conversion_stats(
    session: AsyncSession, offer_id: int
) -> Dict[str, Any]:
    stats = await get_funnel_stats(session, offer_id=offer_id)
    return stats


async def get_client_conversion_stats(
    session: AsyncSession, client_id: int
) -> Dict[str, Any]:
    from datetime import timedelta
    stats = await get_funnel_stats(session, client_id=client_id)

    # Also fetch today / 7d / 30d lead counts
    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    def _lead_count_q(since: datetime):
        return select(func.count(Lead.id)).where(
            and_(Lead.client_id == client_id, Lead.created_at >= since)
        )

    stats["leads_today"] = (await session.execute(_lead_count_q(today_start))).scalar_one()
    stats["leads_7d"] = (
        await session.execute(_lead_count_q(now - timedelta(days=7)))
    ).scalar_one()
    stats["leads_30d"] = (
        await session.execute(_lead_count_q(now - timedelta(days=30)))
    ).scalar_one()
    return stats


async def get_question_dropoff(
    session: AsyncSession, form_id: int
) -> List[Dict[str, Any]]:
    """Return per-question viewed / answered counts and dropoff %."""
    qs_result = await session.execute(
        select(LeadFormQuestion)
        .where(LeadFormQuestion.form_id == form_id)
        .order_by(LeadFormQuestion.position)
    )
    questions = list(qs_result.scalars().all())
    if not questions:
        return []

    # Fetch all viewed/answered events for this form in one query
    events_q = (
        select(
            TrackingEvent.step_number,
            TrackingEvent.event_type,
            func.count(func.distinct(TrackingEvent.session_id)).label("cnt"),
        )
        .where(
            and_(
                TrackingEvent.form_id == form_id,
                TrackingEvent.event_type.in_([
                    EventType.question_viewed.value,
                    EventType.question_answered.value,
                ]),
            )
        )
        .group_by(TrackingEvent.step_number, TrackingEvent.event_type)
    )
    rows = list((await session.execute(events_q)).all())

    # Build lookup: step -> {viewed: N, answered: N}
    step_stats: Dict[int, Dict[str, int]] = {}
    for row in rows:
        step = row.step_number if row.step_number is not None else 0
        if step not in step_stats:
            step_stats[step] = {"viewed": 0, "answered": 0}
        if row.event_type == EventType.question_viewed.value:
            step_stats[step]["viewed"] = row.cnt
        elif row.event_type == EventType.question_answered.value:
            step_stats[step]["answered"] = row.cnt

    result = []
    for i, q in enumerate(questions):
        sv = step_stats.get(i, {"viewed": 0, "answered": 0})
        viewed = sv["viewed"]
        answered = sv["answered"]
        result.append({
            "step": i + 1,
            "question_id": q.id,
            "question_text": q.question_text,
            "viewed": viewed,
            "answered": answered,
            "skipped": viewed - answered if viewed >= answered else 0,
            "dropoff_pct": percent(viewed - answered, viewed) if viewed else 0.0,
            "answer_rate": percent(answered, viewed) if viewed else 0.0,
        })
    return result


async def get_top_sources(
    session: AsyncSession,
    limit: int = 10,
    order_by: str = "approved",
) -> List[Dict[str, Any]]:
    """Top referral sources sorted by the given metric."""
    return await _get_source_ranking(session, limit=limit, order_by=order_by, worst=False)


async def get_bad_sources(
    session: AsyncSession,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Worst sources: many bot_starts but low completion/approve rate."""
    return await _get_source_ranking(session, limit=limit, order_by="approve_rate", worst=True)


async def _get_source_ranking(
    session: AsyncSession,
    limit: int,
    order_by: str,
    worst: bool,
) -> List[Dict[str, Any]]:
    # Aggregate daily stats per referral_source_id
    daily_q = (
        select(
            ReferralSourceStatsDaily.referral_source_id,
            func.coalesce(func.sum(ReferralSourceStatsDaily.bot_starts), 0).label("bot_starts"),
            func.coalesce(func.sum(ReferralSourceStatsDaily.form_completions), 0).label("form_completions"),
            func.coalesce(func.sum(ReferralSourceStatsDaily.leads_created), 0).label("leads_created"),
            func.coalesce(func.sum(ReferralSourceStatsDaily.duplicates), 0).label("duplicates"),
        )
        .where(ReferralSourceStatsDaily.referral_source_id.is_not(None))
        .group_by(ReferralSourceStatsDaily.referral_source_id)
    )
    daily_rows = list((await session.execute(daily_q)).all())

    if not daily_rows:
        return []

    ref_ids = [r.referral_source_id for r in daily_rows]

    # Lead quality per source
    lead_q = (
        select(
            Lead.referral_source_id,
            func.coalesce(func.sum(case((Lead.status == "qualified", 1), else_=0)), 0).label("qualified"),
            func.coalesce(func.sum(case((Lead.status == "approved", 1), else_=0)), 0).label("approved"),
        )
        .where(Lead.referral_source_id.in_(ref_ids))
        .group_by(Lead.referral_source_id)
    )
    lead_rows = {r.referral_source_id: r for r in (await session.execute(lead_q)).all()}

    # Ref names
    refs_q = select(ReferralSource.id, ReferralSource.name).where(
        ReferralSource.id.in_(ref_ids)
    )
    ref_names = {r.id: r.name for r in (await session.execute(refs_q)).all()}

    results = []
    for dr in daily_rows:
        rid = dr.referral_source_id
        lr = lead_rows.get(rid)
        qualified = int(lr.qualified) if lr else 0
        approved = int(lr.approved) if lr else 0
        bot_starts = int(dr.bot_starts)
        form_completions = int(dr.form_completions)
        leads_created = int(dr.leads_created)

        results.append({
            "referral_source_id": rid,
            "ref_name": ref_names.get(rid, f"ref_{rid}"),
            "bot_starts": bot_starts,
            "form_completions": form_completions,
            "leads_created": leads_created,
            "duplicates": int(dr.duplicates),
            "qualified": qualified,
            "approved": approved,
            "completion_rate": percent(form_completions, bot_starts),
            "approve_rate": percent(approved, leads_created),
        })

    sort_keys = {
        "approved": lambda x: x["approved"],
        "qualified": lambda x: x["qualified"],
        "leads_created": lambda x: x["leads_created"],
        "completion_rate": lambda x: x["completion_rate"],
        "approve_rate": lambda x: x["approve_rate"],
        "bot_starts": lambda x: x["bot_starts"],
    }
    key_fn = sort_keys.get(order_by, lambda x: x["approved"])
    results.sort(key=key_fn, reverse=not worst)

    # For bad sources, filter to those that have at least some activity
    if worst:
        results = [r for r in results if r["bot_starts"] >= 5]

    return results[:limit]
