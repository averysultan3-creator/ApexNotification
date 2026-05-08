import pytest

from app.models.lead import SourceType
from app.services.client_service import create_client
from app.services.delivery_service import create_delivery_rule, get_delivery_rule
from app.services.facebook_form_service import create_facebook_form, get_facebook_form_by_fb_form_id
from app.services.facebook_lead_service import create_lead_from_facebook, normalize_lead_data
from app.services.lead_service import get_lead_by_fb_lead_id

pytestmark = pytest.mark.asyncio


async def test_create_lead_from_facebook(session):
    client = await create_client(session, "Client A")
    form = await create_facebook_form(
        session,
        name="Work UA Form",
        fb_page_id="123456789",
        fb_form_id="987654321",
        client_id=client.id,
        offer_name="Remote Work",
    )

    raw = {
        "id": "lead_1",
        "field_data": [
            {"name": "full_name", "values": ["Ivan"]},
            {"name": "phone_number", "values": ["+48000000000"]},
            {"name": "email", "values": ["test@example.com"]},
        ],
    }
    lead = await create_lead_from_facebook(
        session,
        {"leadgen_id": "lead_1", "form_id": "987654321", "page_id": "123456789"},
        raw_details=raw,
    )

    assert lead.id is not None
    assert lead.form_id == form.id
    assert lead.client_id == client.id
    assert lead.full_name == "Ivan"
    assert lead.phone == "+48000000000"
    assert lead.email == "test@example.com"

    fetched = await get_lead_by_fb_lead_id(session, "lead_1")
    assert fetched.id == lead.id


async def test_delivery_rule_lookup(session):
    client = await create_client(session, "Client B")
    form = await create_facebook_form(
        session,
        name="PL Form",
        fb_page_id="page",
        fb_form_id="form",
        client_id=client.id,
    )
    rule = await create_delivery_rule(
        session,
        source_type=SourceType.facebook_lead_form.value,
        source_id=form.id,
        client_id=client.id,
        send_to_admin=True,
        telegram_ids=[123456],
        emails=["client@example.com"],
    )

    fetched = await get_delivery_rule(session, SourceType.facebook_lead_form.value, form.id)
    assert fetched.id == rule.id
    assert fetched.client_id == client.id


async def test_facebook_form_lookup_by_fb_form_id(session):
    client = await create_client(session, "Client C")
    await create_facebook_form(
        session,
        name="Lookup Form",
        fb_page_id="page-1",
        fb_form_id="form-1",
        client_id=client.id,
    )

    fetched = await get_facebook_form_by_fb_form_id(session, "form-1")
    assert fetched is not None
    assert fetched.name == "Lookup Form"


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
