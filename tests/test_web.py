from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.services.apps_script_generator import generate_apps_script
from app.web.api import create_app


def test_health_and_bad_payloads_do_not_500():
    client = TestClient(create_app(), raise_server_exceptions=False)

    assert client.get("/health").status_code == 200
    assert client.post(
        "/webhooks/facebook",
        data="not-json",
        headers={"content-type": "application/json"},
    ).status_code == 400
    assert client.post("/api/google-sheet/lead", json={}).json() == {
        "ok": False,
        "error": "missing_fields",
    }
    assert client.post("/track/page-view", json={}).json() == {
        "ok": False,
        "error": "preland_slug_required",
    }


def test_apps_script_generator_has_required_functions():
    form = SimpleNamespace(
        id=123,
        form_name="Form",
        tag="Tag",
        fb_form_id="fb-1",
        join_code="secret",
        google_sheet_name="Leads",
    )

    code = generate_apps_script(form)

    assert "var BACKEND_URL" in code
    assert "var FUNNEL_ID = 123" in code
    assert "var SECRET = \"secret\"" in code
    assert "var FB_FORM_ID = \"fb-1\"" in code
    assert "var SHEET_NAME = \"Leads\"" in code
    assert "function testConnection()" in code
    assert "function sendTestLead()" in code
    assert "SENT_IDS" in code
