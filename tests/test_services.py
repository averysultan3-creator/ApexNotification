"""Tests for service layer."""
import pytest

from services.client_service import (
    create_client, get_client_by_id, toggle_client_status,
    delete_client, get_clients_paginated,
)
from services.offer_service import create_offer, get_offer_by_id
from services.form_service import create_form, get_form_by_id
from services.referral_service import create_referral, get_ref_by_code
from services.question_service import create_question, get_questions_by_form
from services.lead_service import create_lead, check_duplicate_lead, update_lead_status


pytestmark = pytest.mark.asyncio


# ── Client service ────────────────────────────────────────────────────────────

async def test_create_and_get_client(session):
    client = await create_client(session, name="Test Client", telegram_username="testuser")
    assert client.id is not None
    assert client.name == "Test Client"
    assert client.telegram_username == "testuser"
    assert client.status == "active"

    fetched = await get_client_by_id(session, client.id)
    assert fetched is not None
    assert fetched.name == "Test Client"


async def test_toggle_client_status(session):
    client = await create_client(session, name="Toggle Test")
    assert client.status == "active"
    toggled = await toggle_client_status(session, client.id)
    assert toggled.status == "inactive"
    toggled2 = await toggle_client_status(session, client.id)
    assert toggled2.status == "active"


async def test_delete_client(session):
    client = await create_client(session, name="Delete Me")
    cid = client.id
    result = await delete_client(session, cid)
    assert result is True
    assert await get_client_by_id(session, cid) is None


async def test_clients_pagination(session):
    for i in range(5):
        await create_client(session, name=f"Paginated Client {i}")
    items, total = await get_clients_paginated(session, page=0, page_size=3)
    assert len(items) <= 3
    assert total >= 5


# ── Offer service ─────────────────────────────────────────────────────────────

async def test_create_offer(session):
    client = await create_client(session, name="Client for Offer")
    offer = await create_offer(session, client_id=client.id, name="Test Offer", geo="UA")
    assert offer.id is not None
    assert offer.client_id == client.id
    assert offer.geo == "UA"


# ── Form service ──────────────────────────────────────────────────────────────

async def test_create_form(session):
    client = await create_client(session, name="Form Client")
    offer = await create_offer(session, client_id=client.id, name="Form Offer")
    form = await create_form(
        session,
        client_id=client.id,
        offer_id=offer.id,
        name="Test Form",
        language="ru",
        welcome_text="Hello!",
    )
    assert form.id is not None
    assert form.slug  # auto-generated
    assert form.status == "active"


async def test_form_slug_uniqueness(session):
    client = await create_client(session, name="Slug Client")
    offer = await create_offer(session, client_id=client.id, name="Slug Offer")
    form1 = await create_form(session, client_id=client.id, offer_id=offer.id, name="My Form")
    form2 = await create_form(session, client_id=client.id, offer_id=offer.id, name="My Form")
    assert form1.slug != form2.slug


# ── Referral service ──────────────────────────────────────────────────────────

async def test_create_referral(session):
    client = await create_client(session, name="Ref Client")
    offer = await create_offer(session, client_id=client.id, name="Ref Offer")
    form = await create_form(session, client_id=client.id, offer_id=offer.id, name="Ref Form")
    ref = await create_referral(session, form_id=form.id, name="Facebook Ads", source_type="facebook")
    assert ref.code  # auto-generated 8-char code
    assert len(ref.code) == 8
    fetched = await get_ref_by_code(session, ref.code)
    assert fetched is not None
    assert fetched.id == ref.id


# ── Question service ──────────────────────────────────────────────────────────

async def test_create_questions_ordering(session):
    client = await create_client(session, name="Q Client")
    offer = await create_offer(session, client_id=client.id, name="Q Offer")
    form = await create_form(session, client_id=client.id, offer_id=offer.id, name="Q Form")
    q1 = await create_question(session, form.id, "What is your name?", "text")
    q2 = await create_question(session, form.id, "What is your phone?", "phone")
    q3 = await create_question(session, form.id, "Any comments?", "comment", is_required=False)
    questions = await get_questions_by_form(session, form.id)
    assert len(questions) == 3
    assert questions[0].position < questions[1].position < questions[2].position


# ── Lead service ──────────────────────────────────────────────────────────────

async def test_create_lead(session):
    client = await create_client(session, name="Lead Client")
    offer = await create_offer(session, client_id=client.id, name="Lead Offer")
    form = await create_form(session, client_id=client.id, offer_id=offer.id, name="Lead Form")
    ref = await create_referral(session, form_id=form.id, name="TG source")

    lead = await create_lead(
        session,
        form_id=form.id,
        client_id=client.id,
        offer_id=offer.id,
        referral_source_id=ref.id,
        telegram_user_id=999999,
        telegram_username="testlead",
        first_name="Ivan",
        last_name="Ivanov",
        answers={"Name?": "Ivan Ivanov", "Phone?": "+380971234567"},
    )
    assert lead.id is not None
    assert lead.status == "new"


async def test_duplicate_lead_detection(session):
    client = await create_client(session, name="Dup Client")
    offer = await create_offer(session, client_id=client.id, name="Dup Offer")
    form = await create_form(session, client_id=client.id, offer_id=offer.id, name="Dup Form")
    await create_lead(
        session,
        form_id=form.id, client_id=client.id, offer_id=offer.id,
        referral_source_id=None, telegram_user_id=12345,
        telegram_username=None, first_name=None, last_name=None, answers={},
    )
    is_dup = await check_duplicate_lead(session, form.id, 12345)
    assert is_dup is True
    not_dup = await check_duplicate_lead(session, form.id, 99999)
    assert not_dup is False


async def test_update_lead_status(session):
    client = await create_client(session, name="Status Client")
    offer = await create_offer(session, client_id=client.id, name="Status Offer")
    form = await create_form(session, client_id=client.id, offer_id=offer.id, name="Status Form")
    lead = await create_lead(
        session,
        form_id=form.id, client_id=client.id, offer_id=offer.id,
        referral_source_id=None, telegram_user_id=77777,
        telegram_username=None, first_name=None, last_name=None, answers={},
    )
    updated = await update_lead_status(session, lead.id, "approved")
    assert updated.status == "approved"
