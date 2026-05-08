from app.services.facebook_lead_service import parse_facebook_webhook_payload, verify_facebook_webhook
from app.utils.formatters import percent
from app.utils.validators import is_valid_email, is_valid_slug, normalize_slug, parse_int_list


def test_facebook_webhook_verify():
    assert verify_facebook_webhook("subscribe", "test_verify", "123") == "123"
    assert verify_facebook_webhook("subscribe", "wrong", "123") is None


def test_parse_facebook_webhook_payload():
    payload = {
        "object": "page",
        "entry": [
            {
                "id": "page_1",
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {"leadgen_id": "lead_1", "form_id": "form_1", "page_id": "page_1"},
                    }
                ],
            }
        ],
    }

    assert parse_facebook_webhook_payload(payload) == [
        {"leadgen_id": "lead_1", "form_id": "form_1", "page_id": "page_1"}
    ]


def test_validators_and_percent():
    assert is_valid_slug("remote-ua")
    assert normalize_slug("Remote UA!") == "remote-ua"
    assert is_valid_email("client@example.com")
    assert parse_int_list("123, 456\n789") == [123, 456, 789]
    assert percent(1, 4) == 25.0
    assert percent(1, 0) == 0.0
