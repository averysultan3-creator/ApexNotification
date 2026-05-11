from __future__ import annotations

import json

from app.models.funnel_form import FunnelForm
from config import PUBLIC_BASE_URL


def _js(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def generate_apps_script(form: FunnelForm) -> str:
    backend_url = PUBLIC_BASE_URL.rstrip("/")
    lead_endpoint = f"{backend_url}/api/google-sheet/lead"
    health_endpoint = f"{backend_url}/health"

    template = r'''// Apex Lead Router - Google Sheet bridge
// Funnel: @@FORM_NAME@@
// Funnel ID: @@FUNNEL_ID@@
// FB Form ID: @@FB_FORM_ID@@
//
// Setup:
// 1. Open Google Sheet -> Extensions -> Apps Script.
// 2. Replace all code with this file and save.
// 3. Run setup() once and grant permissions.
// 4. Optional: run testConnection() and sendTestLead().

var BACKEND_URL = @@BACKEND_URL@@;
var BACKEND_HEALTH_URL = @@BACKEND_HEALTH_URL@@;
var FUNNEL_ID = @@FUNNEL_ID@@;
var SECRET = @@SECRET@@;
var FB_FORM_ID = @@FB_FORM_ID_JSON@@;
var SHEET_NAME = @@SHEET_NAME@@;

function setup() {
  ScriptApp.getProjectTriggers().forEach(function(trigger) {
    if (trigger.getHandlerFunction() === "sendNewLeads") {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  ScriptApp.newTrigger("sendNewLeads")
    .timeBased()
    .everyMinutes(1)
    .create();

  Logger.log("Apex trigger created. Running first scan...");
  sendNewLeads();
}

function testConnection() {
  try {
    var resp = UrlFetchApp.fetch(BACKEND_HEALTH_URL, {
      method: "get",
      headers: {"ngrok-skip-browser-warning": "1"},
      muteHttpExceptions: true,
      followRedirects: true
    });
    Logger.log("Health: " + resp.getResponseCode() + " " + resp.getContentText());
    return resp.getResponseCode() === 200;
  } catch (err) {
    Logger.log("Health failed: " + err);
    return false;
  }
}

function sendTestLead() {
  var payload = {
    secret: SECRET,
    funnel_id: FUNNEL_ID,
    external_lead_id: "test_" + Date.now(),
    fb_form_id: FB_FORM_ID,
    form_name: "Test Form",
    full_name: "Test User",
    phone: "+10000000000",
    email: "test@example.com",
    telegram: "@testuser",
    lead_created_time: new Date().toISOString(),
    raw: {source: "sendTestLead"}
  };
  var ok = _sendLead(payload);
  Logger.log(ok ? "Test lead sent OK" : "Test lead failed");
  return ok;
}

function sendNewLeads() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  if (!sheet) {
    Logger.log("Sheet not found: " + SHEET_NAME);
    return;
  }

  var lastRow = sheet.getLastRow();
  var lastCol = sheet.getLastColumn();
  if (lastRow < 2 || lastCol < 1) {
    return;
  }

  var headers = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  var data = sheet.getRange(2, 1, lastRow - 1, lastCol).getValues();
  var props = PropertiesService.getScriptProperties();
  var sent = _loadSentIds(props);
  var changed = false;

  for (var i = 0; i < data.length; i++) {
    var row = data[i];
    var externalId = _getField(headers, row, ["id", "lead_id", "leadId", "ID", "Lead ID"]);
    if (!externalId) {
      externalId = "row_" + (i + 2);
    }

    var key = String(externalId);
    if (sent[key]) {
      continue;
    }

    var payload = _buildPayload(headers, row, key);
    if (_sendLead(payload)) {
      sent[key] = true;
      changed = true;
    }
  }

  if (changed) {
    props.setProperty("SENT_IDS", JSON.stringify(sent));
  }
}

function _buildPayload(headers, row, externalId) {
  var raw = {};
  for (var h = 0; h < headers.length; h++) {
    if (headers[h]) {
      raw[String(headers[h])] = row[h];
    }
  }

  return {
    secret: SECRET,
    funnel_id: FUNNEL_ID,
    external_lead_id: String(externalId),
    fb_form_id: FB_FORM_ID,
    form_name: _getField(headers, row, ["form_name", "form name", "Form Name", "formName"]) || "",
    full_name: _getField(headers, row, ["full_name", "full name", "Full Name", "name", "Name"]) || "",
    phone: _getField(headers, row, ["phone_number", "phone", "Phone", "mobile"]) || "",
    email: _getField(headers, row, ["email", "Email", "e-mail"]) || "",
    telegram: _getField(headers, row, ["telegram", "Telegram", "TELEGRAM", "tg", "TG", "Tg", "Телеграм", "телеграм", "ТЕЛЕГРАМ", "Телеграмм", "telegram_username", "tg_username", "username", "Username", "@telegram", "твой_телеграм", "твой телеграм", "Твой телеграм", "Твой Телеграм", "твій_телеграм", "твій телеграм", "Твій телеграм", "Твій Телеграм", "твiй_телеграм", "Нікнейм", "нікнейм", "нікнейм телеграм", "ник", "Ник", "нік", "Нік"]) || "",
    lead_created_time: _getField(headers, row, ["created_time", "created", "date", "Date"]) || new Date().toISOString(),
    raw: raw
  };
}

function _sendLead(payload) {
  try {
    var resp = UrlFetchApp.fetch(BACKEND_URL, {
      method: "post",
      contentType: "application/json",
      headers: {"ngrok-skip-browser-warning": "1"},
      payload: JSON.stringify(payload),
      muteHttpExceptions: true,
      followRedirects: true
    });
    var code = resp.getResponseCode();
    var body = resp.getContentText();
    Logger.log("Lead " + payload.external_lead_id + " -> " + code + " " + body);
    if (code !== 200) {
      return false;
    }
    var parsed = JSON.parse(body || "{}");
    return parsed.ok === true;
  } catch (err) {
    Logger.log("Send failed: " + err);
    return false;
  }
}

function _loadSentIds(props) {
  try {
    var raw = props.getProperty("SENT_IDS");
    return raw ? JSON.parse(raw) : {};
  } catch (err) {
    Logger.log("SENT_IDS reset after parse error: " + err);
    props.deleteProperty("SENT_IDS");
    return {};
  }
}

function _getField(headers, row, names) {
  for (var n = 0; n < names.length; n++) {
    var needle = String(names[n]).toLowerCase();
    for (var h = 0; h < headers.length; h++) {
      if (String(headers[h]).toLowerCase() === needle) {
        var value = row[h];
        if (value !== "" && value !== null && value !== undefined) {
          return String(value);
        }
      }
    }
  }
  return null;
}

// -------------------------------------------------------
// Emergency helpers — run manually in Apps Script editor
// -------------------------------------------------------

// Reset sent-IDs cache so ALL rows are re-processed on next run.
// The server deduplicates by external_lead_id, so no double-saves.
function resetSentIds() {
  PropertiesService.getScriptProperties().deleteProperty("SENT_IDS");
  Logger.log("SENT_IDS cleared. Next sendNewLeads() run will re-process all rows.");
}

// Force-send all rows right now (same as resetSentIds + sendNewLeads).
function forceResend() {
  resetSentIds();
  sendNewLeads();
  Logger.log("forceResend done.");
}
'''

    return (
        template
        .replace("@@FORM_NAME@@", str(form.form_name))
        .replace("@@FUNNEL_ID@@", str(form.id))
        .replace("@@FB_FORM_ID@@", str(form.fb_form_id))
        .replace("@@FB_FORM_ID_JSON@@", _js(form.fb_form_id))
        .replace("@@BACKEND_URL@@", _js(lead_endpoint))
        .replace("@@BACKEND_HEALTH_URL@@", _js(health_endpoint))
        .replace("@@SECRET@@", _js(form.join_code))
        .replace("@@SHEET_NAME@@", _js(form.google_sheet_name or "Leads"))
    )
