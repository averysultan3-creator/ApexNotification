"""
SiteEvent — tracks visits, CTA-clicks and leave-events from the static
prelanding pages (GitHub Pages).  Populated by analytics_server.py.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Index

from database import Base


class SiteEvent(Base):
    __tablename__ = "site_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # "visit" | "cta_click" | "leave"
    event_type = Column(String(20), nullable=False)
    # UUID generated in JS — links events of one browser session
    session_id = Column(String(36), nullable=False, index=True)
    # e.g. "skyx_pl_1830" — identifies which prelanding sent the event
    site_id = Column(String(100), nullable=True, index=True)
    # UTM ref_code forwarded from the deep-link (?ref=...)
    ref_code = Column(String(100), nullable=True)
    # seconds spent on the page (only for "leave" events)
    time_spent = Column(Integer, nullable=True)
    # first 8 chars of SHA-1(User-Agent) for dedup, no PII stored
    ua_hash = Column(String(8), nullable=True)
    # ISO date string "YYYY-MM-DD" for fast daily aggregation
    date = Column(String(10), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_site_event_type_date", "event_type", "date"),
        Index("ix_site_event_site_date", "site_id", "date"),
    )
