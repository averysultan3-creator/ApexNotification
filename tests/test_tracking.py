import pytest

from app.services.client_service import create_client
from app.services.preland_service import create_preland
from app.services.preland_tracking_service import (
    get_preland_button_stats,
    get_preland_stats,
    track_button_click,
    track_page_view,
)

pytestmark = pytest.mark.asyncio


async def test_preland_page_view_button_click_and_ctr(session):
    client = await create_client(session, "Client A")
    preland = await create_preland(
        session,
        name="Remote Work UA",
        slug="remote-ua",
        url="https://example.github.io/remote-ua/",
        client_id=client.id,
        offer_name="Remote Work",
    )

    await track_page_view(session, "remote-ua", {"url": preland.url, "visitor_id": "v1"}, ip="1.1.1.1")
    await track_page_view(session, "remote-ua", {"url": preland.url, "visitor_id": "v2"}, ip="2.2.2.2")
    await track_button_click(
        session,
        "remote-ua",
        "main_cta",
        {"url": preland.url, "visitor_id": "v1"},
        ip="1.1.1.1",
    )

    stats = await get_preland_stats(session, preland.id)
    buttons = await get_preland_button_stats(session, preland.id)

    assert stats == {"visits": 2, "clicks": 1, "ctr": 50.0}
    assert buttons == {"main_cta": 1}
