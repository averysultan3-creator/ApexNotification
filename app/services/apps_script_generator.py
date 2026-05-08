from __future__ import annotations
from app.models.funnel_form import FunnelForm
from config import PUBLIC_BASE_URL


def generate_apps_script(form: FunnelForm) -> str:
    backend_url = PUBLIC_BASE_URL.rstrip("/")
    lead_endpoint = f"{backend_url}/api/funnel/{form.verify_token}/lead"
    health_endpoint = f"{backend_url}/health"

    return f"""// ============================================================
// AUTO-GENERATED: {form.form_name}
// Тег: {form.tag or '—'}
// FB Form ID: {form.fb_form_id}
// Verify Token: {form.verify_token}
// ============================================================
// КАК ИСПОЛЬЗОВАТЬ:
// 1. Скопируй этот код в Google Sheet → Extensions → Apps Script
// 2. Нажми Deploy → New deployment → Web App
// 3. Execute as: Me | Access: Anyone
// 4. Скопируй Web App URL
// 5. Вставь этот URL в Meta → Webhooks → Callback URL
// 6. В поле Verify Token вставь: {form.verify_token}
// 7. Подпишись на поле: leadgen
// 8. Нажми testConnection() для проверки
// ============================================================

var VERIFY_TOKEN = "{form.verify_token}";
var BACKEND_LEAD_URL = "{lead_endpoint}";
var BACKEND_HEALTH_URL = "{health_endpoint}";

// Шаг 1: Meta проверяет webhook — отвечаем на challenge
function doGet(e) {{
  if (e.parameter["hub.verify_token"] === VERIFY_TOKEN) {{
    return ContentService.createTextOutput(e.parameter["hub.challenge"]);
  }}
  return ContentService.createTextOutput("403 Forbidden");
}}

// Шаг 2: Meta присылает leadgen событие — пересылаем в backend
function doPost(e) {{
  try {{
    var resp = UrlFetchApp.fetch(BACKEND_LEAD_URL, {{
      method: "post",
      contentType: "application/json",
      payload: e.postData.contents,
      muteHttpExceptions: true
    }});
    Logger.log("Backend response: " + resp.getResponseCode() + " " + resp.getContentText());
  }} catch(err) {{
    Logger.log("Error forwarding lead: " + err);
  }}
  return ContentService.createTextOutput("ok");
}}

// Тест: проверить соединение с backend
function testConnection() {{
  try {{
    var resp = UrlFetchApp.fetch(BACKEND_HEALTH_URL, {{muteHttpExceptions: true}});
    Logger.log("Health check: " + resp.getResponseCode() + " " + resp.getContentText());
  }} catch(err) {{
    Logger.log("Connection failed: " + err);
  }}
}}

// Тест: отправить тестовый лид в backend
function testLead() {{
  var testPayload = JSON.stringify({{
    object: "page",
    entry: [{{
      id: "TEST_PAGE_ID",
      changes: [{{
        field: "leadgen",
        value: {{
          leadgen_id: "TEST_LEAD_ID_" + Date.now(),
          form_id: "{form.fb_form_id}",
          page_id: "TEST_PAGE_ID"
        }}
      }}]
    }}]
  }});
  var resp = UrlFetchApp.fetch(BACKEND_LEAD_URL, {{
    method: "post",
    contentType: "application/json",
    payload: testPayload,
    muteHttpExceptions: true
  }});
  Logger.log("Test lead response: " + resp.getResponseCode() + " " + resp.getContentText());
}}
"""
