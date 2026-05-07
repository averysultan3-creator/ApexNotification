"""Client panel keyboards (client_admin, client_viewer)."""
from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models.lead import LEAD_STATUS_LABELS
from utils.pagination import PageResult


class ClCb(CallbackData, prefix="cp"):
    """Client panel callbacks."""
    section: str    # home|stats|leads|links|export|contact|lead|status
    id: int = 0     # lead_id / offer_id / filter value
    page: int = 0
    days: int = 7   # stats period


# ══════════════════════════════════════════════════════════════════════════════

def client_home_kb(can_change_status: bool = True) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📊 Статистика",  callback_data=ClCb(section="stats"))
    b.button(text="📥 Заявки",      callback_data=ClCb(section="leads"))
    b.button(text="🔗 Ссылки",      callback_data=ClCb(section="links"))
    b.button(text="📤 Экспорт",     callback_data=ClCb(section="export"))
    b.button(text="👤 Связаться",   callback_data=ClCb(section="contact"))
    b.adjust(2, 2, 1)
    return b.as_markup()


def client_stats_period_kb(current_days: int = 7) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for days, label in ((1, "Сегодня"), (7, "7 дней"), (30, "30 дней")):
        mark = "•" if days == current_days else " "
        b.button(
            text=f"{mark} {label}",
            callback_data=ClCb(section="stats", days=days),
        )
    b.button(text="📥 Заявки",      callback_data=ClCb(section="leads"))
    b.button(text="📤 Экспорт",     callback_data=ClCb(section="export"))
    b.button(text="🏠 Кабинет",     callback_data=ClCb(section="home"))
    b.adjust(3, 2, 1)
    return b.as_markup()


def client_leads_kb(leads: list, pr: PageResult, current_status: str = "") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for lead in leads:
        status_label = LEAD_STATUS_LABELS.get(lead.status, lead.status)
        name = lead.telegram_username or lead.first_name or str(lead.telegram_user_id)
        b.button(
            text=f"{status_label} — {name}",
            callback_data=ClCb(section="lead", id=lead.id, page=pr.page),
        )
    b.adjust(1)
    # Pagination
    if pr.has_prev:
        b.button(
            text="◀️ Назад",
            callback_data=ClCb(section="leads", page=pr.page - 1),
        )
    if pr.has_next:
        b.button(
            text="▶️ Вперёд",
            callback_data=ClCb(section="leads", page=pr.page + 1),
        )
    # Status filter tabs
    b.button(text="🆕 Новые",     callback_data=ClCb(section="leads", id=0))
    b.button(text="📞 В работе",  callback_data=ClCb(section="leads", id=1))
    b.button(text="✅ Approved",  callback_data=ClCb(section="leads", id=2))
    b.button(text="📤 Экспорт",  callback_data=ClCb(section="export"))
    b.button(text="🏠 Кабинет",  callback_data=ClCb(section="home"))
    b.adjust(1)
    return b.as_markup()


def client_lead_view_kb(lead_id: int, page: int = 0, can_change: bool = True) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if can_change:
        b.button(text="📞 В работе",  callback_data=ClCb(section="status", id=lead_id, page=1))
        b.button(text="✅ Approved",   callback_data=ClCb(section="status", id=lead_id, page=2))
        b.button(text="❌ Не подходит", callback_data=ClCb(section="status", id=lead_id, page=3))
        b.adjust(3)
    b.button(text="◀️ К заявкам",    callback_data=ClCb(section="leads", page=page))
    b.button(text="🏠 Кабинет",       callback_data=ClCb(section="home"))
    b.adjust(1)
    return b.as_markup()


def client_links_kb(refs: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for ref in refs:
        icon = "✅" if ref.status == "active" else "⏸"
        b.button(
            text=f"{icon} {ref.name[:28]}",
            callback_data=ClCb(section="link_view", id=ref.id),
        )
    b.adjust(1)
    b.button(text="🏠 Кабинет", callback_data=ClCb(section="home"))
    return b.as_markup()
