"""formatters.py — human-readable text formatters for Telegram messages."""
import json
from typing import List

from app.models.lead import Lead
from app.models.client import Client
from app.models.facebook_lead_form import FacebookLeadForm
from app.models.delivery_rule import DeliveryRule
from app.models.preland import Preland


def fmt_lead_card(lead: Lead, form: FacebookLeadForm | None = None, client: Client | None = None) -> str:
    lines = [f"📥 <b>Лид #{lead.id}</b>"]
    lines.append("Источник: Facebook Lead Form")
    if form:
        lines.append(f"Форма: {form.name}")
    if client:
        lines.append(f"Клиент: {client.name}")
    if lead.created_at:
        lines.append(f"Дата: {lead.created_at.strftime('%d.%m.%Y %H:%M')}")
    lines.append("")
    if lead.full_name:
        lines.append(f"Имя: {lead.full_name}")
    if lead.phone:
        lines.append(f"Телефон: {lead.phone}")
    if lead.email:
        lines.append(f"Email: {lead.email}")
    if lead.telegram:
        lines.append(f"Telegram: @{lead.telegram}")
    lines.append("")
    lines.append("Доставка:")
    lines.append(f"Telegram: {'✅' if lead.delivered_telegram else '❌'}")
    lines.append(f"Email: {'✅' if lead.delivered_email else '❌'}")
    lines.append(f"Google Sheet: {'✅' if lead.delivered_sheet else '⬜'}")
    return "\n".join(lines)


def fmt_client_card(client: Client) -> str:
    tg_ids: List = json.loads(client.telegram_ids_json or "[]")
    emails: List = json.loads(client.emails_json or "[]")
    lines = [f"👥 <b>{client.name}</b>", ""]
    if tg_ids:
        lines.append("Telegram IDs:")
        for tid in tg_ids:
            lines.append(f"  {tid}")
    else:
        lines.append("Telegram IDs: нет")
    lines.append("")
    if emails:
        lines.append("Emails:")
        for e in emails:
            lines.append(f"  {e}")
    else:
        lines.append("Emails: нет")
    if client.notes:
        lines.append(f"\nЗаметки: {client.notes}")
    return "\n".join(lines)


def fmt_form_card(form: FacebookLeadForm, client: Client | None = None) -> str:
    lines = [
        f"📋 <b>{form.name}</b>",
        f"FB Page ID: <code>{form.fb_page_id}</code>",
        f"FB Form ID: <code>{form.fb_form_id}</code>",
        f"Клиент: {client.name if client else '—'}",
        f"Оффер: {form.offer_name or '—'}",
        f"Статус: {'🟢 активна' if form.status == 'active' else '⏸ пауза'}",
    ]
    return "\n".join(lines)


def fmt_rule_card(rule: DeliveryRule, form: FacebookLeadForm | None = None, client: Client | None = None) -> str:
    tg_ids: List = json.loads(rule.telegram_ids_json or "[]")
    emails: List = json.loads(rule.emails_json or "[]")
    lines = [
        f"🔀 <b>Правило #{rule.id}</b>",
        f"Форма: {form.name if form else f'ID {rule.source_id}'}",
        f"Клиент: {client.name if client else '—'}",
        "",
        "Отправлять:",
        f"{'✅' if rule.send_to_admin else '⬜'} Admin Telegram",
    ]
    for tid in tg_ids:
        lines.append(f"✅ Telegram: {tid}")
    for em in emails:
        lines.append(f"✅ Email: {em}")
    if rule.google_sheet_id:
        lines.append(f"✅ Google Sheet: {rule.google_sheet_id}")
    else:
        lines.append("⬜ Google Sheet")
    return "\n".join(lines)


def fmt_preland_card(preland: Preland, client: Client | None = None, stats: dict | None = None) -> str:
    lines = [
        f"🌐 <b>{preland.name}</b>",
        f"Slug: <code>{preland.slug}</code>",
        f"URL: {preland.url or '—'}",
        f"Клиент: {client.name if client else '—'}",
        f"Оффер: {preland.offer_name or '—'}",
    ]
    if stats:
        lines += [
            "",
            "Сегодня:",
            f"👁 Visits: {stats.get('visits', 0)}",
            f"👆 Clicks: {stats.get('clicks', 0)}",
            f"📈 CTR: {stats.get('ctr', 0)}%",
        ]
    return "\n".join(lines)
