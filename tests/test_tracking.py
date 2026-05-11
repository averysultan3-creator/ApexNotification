import pytest

from app.services.preland_link_service import create_link
from app.services.preland_site_service import create_site
from app.services.preland_tracking_service import (
    generate_tracking_script,
    get_link_button_stats,
    get_link_stats,
    track_button_click,
    track_page_view,
)

pytestmark = pytest.mark.asyncio


async def test_preland_page_view_button_click_and_ctr(session):
    site = await create_site(
        session,
        name="Remote Work UA",
        base_url="https://example.github.io/remote-ua",
    )
    link = await create_link(
        session,
        site=site,
        display_name="Remote UA | UA | Story | Girls",
        slug="remote-ua",
    )

    await track_page_view(
        session,
        "remote-ua",
        {"visitor_id": "v1", "utm_source": "fb", "utm_campaign": "c1"},
        ip="1.1.1.1",
    )
    await track_page_view(session, "remote-ua", {"visitor_id": "v2"})
    await track_button_click(
        session,
        "remote-ua",
        "main_cta",
        {"visitor_id": "v1", "utm_source": "fb", "utm_campaign": "c1"},
    )

    stats = await get_link_stats(session, link.id)
    buttons = await get_link_button_stats(session, link.id)

    assert stats == {"visits": 2, "clicks": 1, "ctr": 50.0}
    assert buttons == {"main_cta": 1}


async def test_dedup_same_visitor_same_event(session):
    """Same visitor_id + same event_type should be stored only once."""
    site = await create_site(session, name="Dedup Site", base_url="https://example.github.io/dedup")
    link = await create_link(session, site=site, display_name="Dedup | PL", slug="dedup-pl")

    await track_page_view(session, "dedup-pl", {"visitor_id": "vX"})
    await track_page_view(session, "dedup-pl", {"visitor_id": "vX"})  # duplicate

    stats = await get_link_stats(session, link.id)
    assert stats["visits"] == 1


async def test_tracking_script_uses_sendbeacon_and_fallback():
    script = generate_tracking_script("remote-ua", base_url="https://backend.test")

    assert "try{" in script
    assert "sendBeacon" in script
    assert "new Image()" in script
    assert "/track/pv" in script
    assert "/track/bc" in script
    assert "utm_source" in script
    assert "data-track-click" in script
    assert "preventDefault" not in script


async def test_tracking_script_no_pl_uses_url_param():
    """When slug=None, script must read ?pl= from URL at runtime."""
    script = generate_tracking_script(slug=None, base_url="https://backend.test")
    assert "_p.get('pl')" in script


async def test_unknown_slug_stores_event_without_link_id(session):
    """If slug has no PrelandLink, event is still recorded (link_id=None, slug set)."""
    event = await track_page_view(session, "unknown-slug", {"visitor_id": "v1"})
    assert event is not None
    assert event.slug == "unknown-slug"
    assert event.link_id is None
