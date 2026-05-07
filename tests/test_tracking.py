"""Tests for the tracking service and export analytics service."""
import os
os.environ.setdefault("BOT_TOKEN", "0:test")
os.environ.setdefault("ADMIN_IDS", "12345")

import pytest
import pytest_asyncio
from sqlalchemy import select

from models.tracking_event import TrackingEvent, EventType
from models.tracking_session import TrackingSession, SessionStatus
from models.referral_source_stats_daily import ReferralSourceStatsDaily
from services.tracking_service import (
    new_session_id,
    track_event,
    start_tracking_session,
    track_form_started,
    track_question_viewed,
    track_question_answered,
    track_form_completed,
    track_lead_created,
    track_duplicate_detected,
    track_lead_status_changed,
    get_funnel_stats,
    get_question_dropoff,
    _inc_daily,
    percent,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sid() -> str:
    return new_session_id()


# ── 1. percent() safe division ────────────────────────────────────────────────

def test_percent_safe_division():
    assert percent(10, 100) == 10.0
    assert percent(1, 3) == 33.3
    assert percent(0, 0) == 0.0
    assert percent(5, 0) == 0.0


# ── 2. track_event creates a TrackingEvent row ───────────────────────────────

@pytest.mark.asyncio
async def test_track_event_creates_row(session):
    sid = _sid()
    event = await track_event(
        session, EventType.bot_started.value,
        session_id=sid, form_id=1, client_id=1, offer_id=1,
        referral_source_id=1, telegram_user_id=100,
    )
    await session.flush()
    result = await session.execute(
        select(TrackingEvent).where(TrackingEvent.session_id == sid)
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].event_type == EventType.bot_started.value
    assert rows[0].telegram_user_id == 100


# ── 3. start_tracking_session creates session + 2 events + daily stats ────────

@pytest.mark.asyncio
async def test_start_tracking_session(session):
    sid = _sid()
    ts = await start_tracking_session(
        session,
        session_id=sid, form_id=2, client_id=1, offer_id=1,
        referral_source_id=2, telegram_user_id=200,
        telegram_username="testuser", total_steps=5,
    )
    await session.flush()

    # TrackingSession created
    assert ts is not None
    assert ts.session_id == sid
    assert ts.status == SessionStatus.started.value
    assert ts.total_steps == 5

    # 2 events: bot_started + form_viewed
    events = (await session.execute(
        select(TrackingEvent).where(TrackingEvent.session_id == sid)
    )).scalars().all()
    event_types = {e.event_type for e in events}
    assert EventType.bot_started.value in event_types
    assert EventType.form_viewed.value in event_types

    # Daily stats updated
    daily = (await session.execute(
        select(ReferralSourceStatsDaily).where(
            ReferralSourceStatsDaily.referral_source_id == 2,
            ReferralSourceStatsDaily.form_id == 2,
        )
    )).scalar_one_or_none()
    assert daily is not None
    assert daily.bot_starts >= 1
    assert daily.form_views >= 1


# ── 4. track_form_started updates session status ─────────────────────────────

@pytest.mark.asyncio
async def test_track_form_started(session):
    sid = _sid()
    await start_tracking_session(
        session,
        session_id=sid, form_id=3, client_id=1, offer_id=1,
        referral_source_id=3, telegram_user_id=300, total_steps=3,
    )
    await track_form_started(
        session, sid,
        form_id=3, client_id=1, offer_id=1, referral_source_id=3,
        telegram_user_id=300,
    )
    await session.flush()

    ts = (await session.execute(
        select(TrackingSession).where(TrackingSession.session_id == sid)
    )).scalar_one_or_none()
    assert ts.status == SessionStatus.in_progress.value


# ── 5. track_form_completed marks session completed ──────────────────────────

@pytest.mark.asyncio
async def test_track_form_completed(session):
    sid = _sid()
    await start_tracking_session(
        session,
        session_id=sid, form_id=4, client_id=1, offer_id=1,
        referral_source_id=4, telegram_user_id=400, total_steps=2,
    )
    await track_form_completed(
        session, sid,
        form_id=4, client_id=1, offer_id=1, referral_source_id=4,
        telegram_user_id=400,
    )
    await session.flush()

    ts = (await session.execute(
        select(TrackingSession).where(TrackingSession.session_id == sid)
    )).scalar_one_or_none()
    assert ts.is_completed is True
    assert ts.status == SessionStatus.completed.value
    assert ts.completed_at is not None


# ── 6. track_duplicate_detected marks session as duplicate ───────────────────

@pytest.mark.asyncio
async def test_track_duplicate_detected(session):
    sid = _sid()
    await start_tracking_session(
        session,
        session_id=sid, form_id=5, client_id=1, offer_id=1,
        referral_source_id=5, telegram_user_id=500, total_steps=0,
    )
    await track_duplicate_detected(
        session, sid,
        form_id=5, client_id=1, offer_id=1, referral_source_id=5,
        telegram_user_id=500,
    )
    await session.flush()

    ts = (await session.execute(
        select(TrackingSession).where(TrackingSession.session_id == sid)
    )).scalar_one_or_none()
    assert ts.is_duplicate is True

    # Daily stats duplicates counter
    daily = (await session.execute(
        select(ReferralSourceStatsDaily).where(
            ReferralSourceStatsDaily.referral_source_id == 5,
            ReferralSourceStatsDaily.form_id == 5,
        )
    )).scalar_one_or_none()
    assert daily is not None
    assert daily.duplicates >= 1


# ── 7. _inc_daily accumulates correctly ──────────────────────────────────────

@pytest.mark.asyncio
async def test_inc_daily_accumulates(session):
    kw = dict(referral_source_id=99, form_id=99, client_id=1, offer_id=1, column="leads_created")
    await _inc_daily(session, **kw)
    await _inc_daily(session, **kw)
    await _inc_daily(session, **kw)
    await session.flush()

    daily = (await session.execute(
        select(ReferralSourceStatsDaily).where(
            ReferralSourceStatsDaily.referral_source_id == 99,
            ReferralSourceStatsDaily.form_id == 99,
        )
    )).scalar_one_or_none()
    assert daily is not None
    assert daily.leads_created == 3
