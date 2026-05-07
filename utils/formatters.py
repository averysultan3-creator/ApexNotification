import json
from models.client import Client
from models.offer import Offer
from models.lead_form import LeadForm
from models.lead_form_question import LeadFormQuestion
from models.referral_source import ReferralSource
from models.lead import Lead, LEAD_STATUS_LABELS


STATUS_ICON = {"active": "✅", "inactive": "⏸"}


def fmt_status_icon(status: str) -> str:
    return STATUS_ICON.get(status, "❓")


def fmt_client(c: Client) -> str:
    lines = [
        f"👤 <b>{c.name}</b>",
        f"ID: <code>{c.id}</code>",
        f"Статус: {fmt_status_icon(c.status)} {c.status}",
    ]
    if c.telegram_username:
        lines.append(f"Telegram: @{c.telegram_username}")
    if c.notes:
        lines.append(f"Заметки: {c.notes}")
    lines.append(f"Офферов: {len(c.offers)}")
    lines.append(f"Форм: {len(c.lead_forms)}")
    lines.append(f"Создан: {c.created_at.strftime('%d.%m.%Y') if c.created_at else '—'}")
    return "\n".join(lines)


def fmt_offer(o: Offer) -> str:
    lines = [
        f"📦 <b>{o.name}</b>",
        f"ID: <code>{o.id}</code>",
        f"Клиент: {o.client.name if o.client else '—'}",
        f"Статус: {fmt_status_icon(o.status)} {o.status}",
    ]
    if o.geo:
        lines.append(f"GEO: {o.geo}")
    if o.language:
        lines.append(f"Язык: {o.language}")
    if o.description:
        lines.append(f"Описание: {o.description}")
    lines.append(f"Создан: {o.created_at.strftime('%d.%m.%Y') if o.created_at else '—'}")
    return "\n".join(lines)


def fmt_form(f: LeadForm) -> str:
    lines = [
        f"📝 <b>{f.name}</b>",
        f"ID: <code>{f.id}</code>",
        f"Slug: <code>{f.slug}</code>",
        f"Клиент: {f.client.name if f.client else '—'}",
        f"Оффер: {f.offer.name if f.offer else '—'}",
        f"Язык: {f.language}",
        f"Статус: {fmt_status_icon(f.status)} {f.status}",
        f"Вопросов: {len(f.questions)}",
        f"Рефок: {len(f.referral_sources)}",
    ]
    if f.welcome_text:
        lines.append(f"\n👋 Welcome:\n{f.welcome_text[:100]}...")
    if f.success_text:
        lines.append(f"\n✅ Success:\n{f.success_text[:100]}...")
    return "\n".join(lines)


def fmt_question(q: LeadFormQuestion, num: int) -> str:
    req = "❗" if q.is_required else "⬜"
    lines = [f"{req} <b>{num}. {q.question_text}</b>", f"Тип: {q.question_type}"]
    if q.options_json:
        try:
            opts = json.loads(q.options_json)
            lines.append("Варианты: " + ", ".join(opts))
        except Exception:
            pass
    return "\n".join(lines)


def fmt_ref(r: ReferralSource, bot_username: str = "") -> str:
    link = f"https://t.me/{bot_username}?start=lf_{r.form_id}_ref_{r.code}" if bot_username else ""
    lines = [
        f"🔗 <b>{r.name}</b>",
        f"ID: <code>{r.id}</code>",
        f"Код: <code>{r.code}</code>",
        f"Тип: {r.source_type}",
        f"Статус: {fmt_status_icon(r.status)} {r.status}",
    ]
    if r.notes:
        lines.append(f"Заметки: {r.notes}")
    if link:
        lines.append(f"\n🔗 Ссылка:\n<code>{link}</code>")
    return "\n".join(lines)


def fmt_lead(lead: Lead) -> str:
    status_label = LEAD_STATUS_LABELS.get(lead.status, lead.status)
    name_parts = [p for p in [lead.first_name, lead.last_name] if p]
    full_name = " ".join(name_parts) or "—"

    lines = [
        f"📥 <b>Лид #{lead.id}</b>",
        f"Статус: {status_label}",
        f"Имя: {full_name}",
        f"TG ID: <code>{lead.telegram_user_id}</code>",
    ]
    if lead.telegram_username:
        lines.append(f"Username: @{lead.telegram_username}")
    if lead.client:
        lines.append(f"Клиент: {lead.client.name}")
    if lead.offer:
        lines.append(f"Оффер: {lead.offer.name}")
    if lead.form:
        lines.append(f"Форма: {lead.form.name}")
    if lead.referral_source:
        lines.append(f"Источник: {lead.referral_source.name}")
    if lead.answers_json:
        try:
            answers = json.loads(lead.answers_json)
            lines.append("\n<b>Ответы:</b>")
            for q_text, answer in answers.items():
                lines.append(f"  • {q_text}: {answer}")
        except Exception:
            pass
    if lead.admin_notes:
        lines.append(f"\nЗаметки: {lead.admin_notes}")
    lines.append(f"\nСоздан: {lead.created_at.strftime('%d.%m.%Y %H:%M') if lead.created_at else '—'}")
    return "\n".join(lines)
