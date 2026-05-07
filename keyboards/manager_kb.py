"""Manager panel keyboards."""
from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models.lead import LEAD_STATUS_LABELS
from utils.pagination import PageResult


class MgrCb(CallbackData, prefix="mg"):
    """Manager panel callbacks."""
    section: str   # home|new|working|approved|stats|lead|status
    id: int = 0
    page: int = 0


# ══════════════════════════════════════════════════════════════════════════════

def manager_home_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🆕 Новые",      callback_data=MgrCb(section="new"))
    b.button(text="📞 В работе",   callback_data=MgrCb(section="working"))
    b.button(text="✅ Approved",   callback_data=MgrCb(section="approved"))
    b.button(text="📊 Статистика", callback_data=MgrCb(section="stats"))
    b.adjust(2, 2)
    return b.as_markup()


def manager_leads_kb(leads: list, pr: PageResult, status: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for lead in leads:
        status_label = LEAD_STATUS_LABELS.get(lead.status, lead.status)
        name = lead.telegram_username or lead.first_name or str(lead.telegram_user_id)
        b.button(
            text=f"{status_label} — {name}",
            callback_data=MgrCb(section="lead", id=lead.id, page=pr.page),
        )
    b.adjust(1)
    if pr.has_prev:
        b.button(text="◀️", callback_data=MgrCb(section=status, page=pr.page - 1))
    if pr.has_next:
        b.button(text="▶️", callback_data=MgrCb(section=status, page=pr.page + 1))
    b.button(text="🏠 Кабинет", callback_data=MgrCb(section="home"))
    b.adjust(1)
    return b.as_markup()


def manager_lead_view_kb(lead_id: int, page: int = 0, status: str = "new") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📞 Contacted",  callback_data=MgrCb(section="status", id=lead_id, page=1))
    b.button(text="✅ Qualified",  callback_data=MgrCb(section="status", id=lead_id, page=2))
    b.button(text="🔥 Approved",   callback_data=MgrCb(section="status", id=lead_id, page=3))
    b.button(text="❌ Rejected",   callback_data=MgrCb(section="status", id=lead_id, page=4))
    b.adjust(2, 2)
    b.button(text="◀️ К лидам",   callback_data=MgrCb(section=status, page=page))
    b.button(text="🏠 Кабинет",    callback_data=MgrCb(section="home"))
    b.adjust(1)
    return b.as_markup()
