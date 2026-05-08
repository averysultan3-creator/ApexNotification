import json
from datetime import datetime
from typing import Any
from config import PUBLIC_BASE_URL


def load_json_list(raw: str | None) -> list[Any]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def percent(part: int, total: int) -> float:
    if not total:
        return 0.0
    return round(part / total * 100, 1)


def fmt_dt(value: datetime | None) -> str:
    if not value:
        return "—"
    return value.strftime("%d.%m.%Y %H:%M")


def format_dashboard(data: dict[str, Any]) -> str:
    return (
        "\U0001F3E0 <b>Apex Lead Router</b>\n\n"
        "Сегодня:\n"
        f"\U0001F4E5 Лидов: {data.get('leads_today', 0)}\n"
        f"\u2705 Доставлено: {data.get('delivered_today', 0)}\n"
        f"\u26A0\uFE0F Ошибок: {data.get('delivery_errors_today', 0)}\n\n"
        "Prelands:\n"
        f"\U0001F441 Заходов: {data.get('preland_visits_today', 0)}\n"
        f"\U0001F446 Кликов: {data.get('preland_clicks_today', 0)}\n"
        f"\U0001F4C8 CTR: {data.get('preland_ctr_today', 0)}%\n\n"
        "Что открыть?"
    )


def format_lead_notification(lead: Any) -> str:
    """Чистое уведомление для получателя (клиента)."""
    _d = "—"
    try:
        tag = lead.tag or (lead.funnel_form.tag if lead.funnel_form else None) or _d
        form_name = lead.funnel_form.form_name if lead.funnel_form else _d
    except Exception:
        tag = _d
        form_name = _d

    lines = [
        "\U0001F525 <b>Новый лид!</b>",
        "",
        f"\U0001F3F7 <b>Тег:</b> {tag}",
        f"\U0001F4CB <b>Форма:</b> {form_name}",
        "",
        f"\U0001F464 <b>Имя:</b> {lead.full_name or _d}",
        f"\U0001F4DE <b>Телефон:</b> {lead.phone or _d}",
    ]
    if lead.email:
        lines.append(f"\U0001F4E7 <b>Email:</b> {lead.email}")
    lines += ["", f"\U0001F552 <b>Дата:</b> {fmt_dt(lead.created_at)}"]
    return "\n".join(lines)


def format_lead_card(lead: Any) -> str:
    """Полная карточка лида для администратора."""
    _d = "—"
    try:
        form_name = lead.funnel_form.form_name if lead.funnel_form else _d
        tag = lead.tag or (lead.funnel_form.tag if lead.funnel_form else None) or _d
    except Exception:
        form_name = _d
        tag = _d

    adm = "\u2705" if lead.delivered_admin else "\u274C"
    cli = "\u2705" if lead.delivered_clients else "\u2014"
    sh = "\u2705" if lead.delivered_sheet else "\u2014"

    text = (
        f"\U0001F4E5 <b>Лид #{lead.id}</b>\n\n"
        f"Форма: {form_name}\n"
        f"Тег: {tag}\n"
        f"Дата: {fmt_dt(lead.created_at)}\n\n"
        f"Имя: {lead.full_name or _d}\n"
        f"Телефон: {lead.phone or _d}\n"
        f"Email: {lead.email or _d}\n\n"
        f"Доставка:\n"
        f"Админ: {adm}  Клиенты: {cli}  Sheet: {sh}\n"
    )
    if lead.delivery_error:
        text += f"\n\u26A0\uFE0F {lead.delivery_error[:200]}"
    return text


def format_funnel_card(form: Any, leads_total: int, leads_today: int, recipients_count: int) -> str:
    _d = "—"
    sheet_status = "✅ подключён" if form.google_sheet_id else "❌ не подключён"
    status_icon = "🟢" if form.status == "active" else "🔴"
    return (
        f"{status_icon} <b>{form.form_name}</b>\n\n"
        f"Тег: {form.tag or _d}\n"
        f"FB Form ID: <code>{form.fb_form_id}</code>\n\n"
        f"Получателей: {recipients_count}\n"
        f"Лидов всего: {leads_total}\n"
        f"Лидов сегодня: {leads_today}\n\n"
        f"Google Sheet: {sheet_status}"
    )
