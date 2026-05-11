import pytest

from app.models.lead import Lead
from app.models.lead_delivery_history import DeliveryStatus, LeadDeliveryHistory
from app.services.client_recipient_service import get_or_create_recipient
from app.services.facebook_lead_service import (
    normalize_lead_data,
    process_facebook_lead,
)
from app.services.funnel_form_service import (
    create_funnel_form,
    get_form_by_fb_form_id,
)
from app.services.google_sheet_service import handle_google_sheet_lead
from app.services.lead_service import get_lead_by_fb_lead_id
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id, text, **kwargs):
        self.messages.append((chat_id, text, kwargs))


async def test_funnel_form_recipient_and_facebook_lead_delivery(session, monkeypatch):
    form = await create_funnel_form(
        session,
        form_name="Work UA",
        fb_form_id="form-1",
        fb_page_id="page-1",
        tag="offer-a",
    )
    recipient, created, _reactivated = await get_or_create_recipient(
        session,
        funnel_form_id=form.id,
        telegram_user_id=777,
        telegram_username="client",
        first_name="Client",
    )

    assert created is True
    assert recipient.funnel_form_id == form.id
    assert (await get_form_by_fb_form_id(session, "form-1")).id == form.id

    async def fake_fetch(_leadgen_id):
        return {
            "field_data": [
                {"name": "full_name", "values": ["Anna"]},
                {"name": "phone_number", "values": ["+380971234567"]},
                {"name": "email", "values": ["anna@example.com"]},
            ]
        }

    monkeypatch.setattr("app.services.facebook_lead_service.fetch_lead_details", fake_fetch)

    bot = FakeBot()
    payload = {
        "entry": [{
            "id": "page-1",
            "changes": [{
                "field": "leadgen",
                "value": {"leadgen_id": "lead-1", "form_id": "form-1", "page_id": "page-1"},
            }],
        }]
    }
    leads = await process_facebook_lead(session, payload, bot=bot)

    assert len(leads) == 1
    lead = await get_lead_by_fb_lead_id(session, "lead-1")
    assert lead.full_name == "Anna"
    assert lead.funnel_form_id == form.id
    assert lead.delivered_clients is True
    assert lead.delivered_recipients_count == 1
    assert any(chat_id == 777 for chat_id, _, _ in bot.messages)

    history = (await session.execute(
        select(LeadDeliveryHistory).where(LeadDeliveryHistory.lead_id == lead.id)
    )).scalar_one()
    assert history.recipient_telegram_id == 777
    assert history.status == DeliveryStatus.sent.value


async def test_google_sheet_duplicate_is_scoped_to_funnel(session):
    form_a = await create_funnel_form(session, form_name="A", fb_form_id="fb-a")
    form_b = await create_funnel_form(session, form_name="B", fb_form_id="fb-b")

    base_payload = {
        "secret": form_a.join_code,
        "funnel_id": form_a.id,
        "external_lead_id": "row_2",
        "fb_form_id": "fb-a",
        "full_name": "Lead A",
    }
    first = await handle_google_sheet_lead(session, None, base_payload)
    duplicate = await handle_google_sheet_lead(session, None, base_payload)
    other = await handle_google_sheet_lead(session, None, {
        **base_payload,
        "secret": form_b.join_code,
        "funnel_id": form_b.id,
        "fb_form_id": "fb-b",
        "full_name": "Lead B",
    })

    assert first["ok"] is True
    assert duplicate["duplicate"] is True
    assert other["ok"] is True

    rows = (await session.execute(select(Lead).order_by(Lead.id))).scalars().all()
    assert len(rows) == 2
    assert {row.funnel_form_id for row in rows} == {form_a.id, form_b.id}
    assert all(row.fb_lead_id is None for row in rows)


async def test_google_sheet_rejects_bad_payload(session):
    result = await handle_google_sheet_lead(
        session,
        None,
        {"funnel_id": "abc", "secret": "x", "external_lead_id": "1"},
    )
    assert result == {"ok": False, "error": "invalid_funnel_id"}


async def test_normalize_lead_data():
    normalized = normalize_lead_data(
        {
            "field_data": [
                {"name": "name", "values": ["Anna"]},
                {"name": "phone", "values": ["+380971234567"]},
                {"name": "email", "values": ["anna@example.com"]},
            ]
        }
    )

    assert normalized["full_name"] == "Anna"
    assert normalized["phone"] == "+380971234567"
    assert normalized["email"] == "anna@example.com"
