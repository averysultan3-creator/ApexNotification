import json
from datetime import datetime
from typing import Any
from config import FACEBOOK_VERIFY_TOKEN, PUBLIC_BASE_URL


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
        return "-"
    return value.strftime("%d.%m.%Y %H:%M")


def format_dashboard(data: dict[str, Any]) -> str:
    return (
        "\U0001F3E0 <b>Apex Lead Router</b>\n\n"
        "Сегодня:\n"
        f"\U0001F4E5 Лидов: {data['leads_today']}\n"
        f"\u2705 Доставлено: {data['delivered_today']}\n"
        f"\u26A0\uFE0F Ошибок: {data['delivery_errors_today']}\n\n"
        "Prelands:\n"
        f"\U0001F441 Заходов: {data['preland_visits_today']}\n"
        f"\U0001F446 Кликов: {data['preland_clicks_today']}\n"
        f"\U0001F4C8 CTR: {data['preland_ctr_today']}%\n\n"
        "Что открыть?"
    )


def format_lead_card(lead: Any) -> str:
    """Полная карточка лида для администратора."""
    form_name = ""
    client_name = ""
    try:
        if lead.form:
            form_name = lead.form.name
        if lead.client:
            client_name = lead.client.name
    except Exception:
        pass

    tg_s = "\u2705" if lead.delivered_telegram else "\u274C"
    sh_s = "\u2705" if lead.delivered_sheet else "\u2014"
    _d = "—"

    text = (
        f"\U0001F4E5 <b>Лид #{lead.id}</b>\n\n"
        f"Клиент: {client_name or _d}\n"
        f"Форма: {form_name or _d}\n"
        f"Дата: {fmt_dt(lead.created_at)}\n\n"
        f"Имя: {lead.full_name or _d}\n"
        f"Телефон: {lead.phone or _d}\n"
        f"Email: {lead.email or _d}\n"
        f"Тег: {lead.tag or _d}\n\n"
        f"Доставка:\n"
        f"Telegram: {tg_s}\n"
        f"Google Sheet: {sh_s}\n"
    )
    if lead.delivery_error:
        text += f"\n\u26A0\uFE0F Ошибка: {lead.delivery_error[:200]}"
    return text


def format_lead_notification(lead: Any) -> str:
    """Чистое уведомление о лиде для получателя (клиентская сторона)."""
    _d = "—"
    try:
        tag = lead.tag or (lead.form.name if lead.form else None) or _d
    except Exception:
        tag = _d

    lines = [
        "\U0001F525 <b>Новый лид!</b>",
        "",
        f"\U0001F3F7 <b>Тег:</b> {tag}",
        f"\U0001F4C5 <b>Дата:</b> {fmt_dt(lead.created_at)}",
        "",
        f"\U0001F464 <b>Имя:</b> {lead.full_name or _d}",
        f"\U0001F4DE <b>Телефон:</b> {lead.phone or _d}",
    ]
    if lead.email:
        lines.append(f"\U0001F4E7 <b>Email:</b> {lead.email}")
    return "\n".join(lines)
