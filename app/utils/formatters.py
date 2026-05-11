from __future__ import annotations

import json
from datetime import datetime
from html import escape
from typing import Any


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


def fmt_date(value: datetime | None) -> str:
    if not value:
        return "-"
    return value.strftime("%d.%m")


def html_escape(value: Any) -> str:
    return escape(str(value), quote=False)


def format_dashboard(data: dict[str, Any]) -> str:
    errors = data.get("delivery_errors_today", 0)
    error_line = (
        f"\n\n⚠\ufe0f Ошибок доставки: {errors}. Откройте Лиды → Ошибки."
        if errors else ""
    )
    return (
        "<b>Apex Lead Router</b>\n\n"
        "Сегодня:\n"
        f"Лиды: {data.get('leads_today', 0)}\n"
        f"Доставлено клиентам: {data.get('delivered_today', 0)}\n"
        f"Ошибок доставки: {errors}\n\n"
        "Преленды:\n"
        f"Просмотры: {data.get('preland_visits_today', 0)}\n"
        f"Клики: {data.get('preland_clicks_today', 0)}\n"
        f"CTR: {data.get('preland_ctr_today', 0)}%"
        f"{error_line}\n\n"
        "Выберите действие."
    )


def _lead_core(lead: Any) -> dict[str, str]:
    empty = "-"
    try:
        tag = lead.tag or (lead.funnel_form.tag if lead.funnel_form else None) or empty
        funnel_name = (
            lead.form_name
            or (lead.funnel_form.form_name if lead.funnel_form else None)
            or empty
        )
    except Exception:
        tag = empty
        funnel_name = empty

    date_val = getattr(lead, "lead_created_time", None) or getattr(lead, "created_at", None)
    return {
        "tag": html_escape(tag),
        "funnel_name": html_escape(funnel_name),
        "full_name": html_escape(getattr(lead, "full_name", None) or empty),
        "phone": html_escape(getattr(lead, "phone", None) or empty),
        "telegram": html_escape(getattr(lead, "telegram", None) or empty),
        "email": html_escape(getattr(lead, "email", None) or empty),
        "date": fmt_dt(date_val),
    }


def format_lead_for_client(lead: Any, *, is_archive: bool = False) -> str:
    f = _lead_core(lead)
    header = "<b>\U0001f4e6 Архивный лид</b>" if is_archive else "<b>\U0001f514 Новый лид</b>"
    lines = [
        header,
        "",
        f"<b>Тег:</b> {f['tag']}",
        "",
        f"<b>Воронка:</b>\n{f['funnel_name']}",
        "",
        f"<b>Имя:</b>\n{f['full_name']}",
        "",
        f"<b>Телефон:</b>\n{f['phone']}",
        "",
        f"<b>Telegram:</b>\n{f['telegram']}",
    ]
    if f["email"] != "-":
        lines += ["", f"<b>Email:</b>\n{f['email']}"]
    lines += ["", f"<b>Дата:</b>\n{f['date']}"]
    return "\n".join(lines)


def format_lead_for_admin(lead: Any) -> str:
    f = _lead_core(lead)
    cnt = getattr(lead, "delivered_recipients_count", 0)
    err_line = (
        f"\nWarning: {html_escape(str(lead.delivery_error)[:120])}"
        if getattr(lead, "delivery_error", None) else ""
    )
    return (
        f"<b>Lead #{lead.id}</b>\n\n"
        f"<b>Funnel:</b>\n{f['funnel_name']}\n\n"
        f"<b>Recipients:</b>\n{cnt}\n\n"
        f"<b>Name:</b>\n{f['full_name']}\n\n"
        f"<b>Phone:</b>\n{f['phone']}\n\n"
        f"<b>Telegram:</b>\n{f['telegram']}\n\n"
        f"<b>Email:</b>\n{f['email']}\n\n"
        f"<b>Date:</b>\n{f['date']}\n\n"
        f"<b>Delivery:</b>\nClients: {cnt}{err_line}"
    )


def format_lead_notification(lead: Any) -> str:
    return format_lead_for_client(lead)


def format_lead_card(lead: Any) -> str:
    return format_lead_for_admin(lead)


def format_funnel_card(
    form: Any,
    leads_total: int,
    leads_today: int,
    delivered_today: int,
    errors_today: int,
    recipients_count: int,
) -> str:
    sheet_info = html_escape(form.google_sheet_id) if form.google_sheet_id else "не подключен"
    status = "\U0001f7e2 активна" if form.status == "active" else "⏸ на паузе"
    no_clients_warn = (
        "\n\n⚠\ufe0f Нет активных получателей. Лиды сохраняются, но не доставляются."
        if recipients_count == 0 else ""
    )
    return (
        f"<b>Воронка:</b>\n{html_escape(form.form_name)}\n\n"
        f"<b>Тег:</b>\n{html_escape(form.tag or '-')}\n\n"
        f"<b>Статус:</b>\n{status}\n\n"
        f"<b>Подключения:</b>\n"
        f"Google Sheet: {sheet_info}\n"
        f"Получатели: {recipients_count}\n\n"
        f"<b>Статистика:</b>\n"
        f"Всего лидов: {leads_total}\n"
        f"Сегодня лидов: {leads_today}\n"
        f"Доставлено сегодня: {delivered_today}\n"
        f"Ошибок сегодня: {errors_today}"
        f"{no_clients_warn}"
    )
