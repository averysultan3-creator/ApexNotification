"""
All inline keyboards + CallbackData definitions for the admin area.
"""
from __future__ import annotations

from typing import List, Optional

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models.client import Client
from models.offer import Offer
from models.lead_form import LeadForm
from models.lead_form_question import LeadFormQuestion
from models.referral_source import ReferralSource
from models.lead import Lead, LEAD_STATUS_LABELS
from utils.pagination import PageResult


# ══════════════════════════════════════════════════════════════════════════════
# CallbackData definitions
# ══════════════════════════════════════════════════════════════════════════════

class MenuCb(CallbackData, prefix="mn"):
    section: str


class ClientCb(CallbackData, prefix="cl"):
    action: str
    id: int = 0
    page: int = 0


class OfferCb(CallbackData, prefix="of"):
    action: str
    id: int = 0
    client_id: int = 0
    page: int = 0


class FormCb(CallbackData, prefix="lf"):
    action: str
    id: int = 0
    page: int = 0


class FormEditCb(CallbackData, prefix="lfe"):
    field: str
    id: int = 0


class QuestionCb(CallbackData, prefix="qu"):
    action: str
    id: int = 0
    form_id: int = 0


class RefCb(CallbackData, prefix="rf"):
    action: str
    id: int = 0
    form_id: int = 0
    page: int = 0


class LeadCb(CallbackData, prefix="ld"):
    action: str
    id: int = 0
    page: int = 0


class LeadStatusCb(CallbackData, prefix="lds"):
    lead_id: int
    status: str


class LeadFilterCb(CallbackData, prefix="ldf"):
    field: str
    # encoded value: integer id as string, or empty = reset
    val: str = ""
    page: int = 0


class StatsCb(CallbackData, prefix="st"):
    action: str        # global | client | offer | form | ref
    id: int = 0


class ExportCb(CallbackData, prefix="ex"):
    action: str
    fmt: str = ""


class ConfirmCb(CallbackData, prefix="conf"):
    action: str    # yes | no
    target: str    # e.g. "del_client_5"


class CancelCb(CallbackData, prefix="cancel"):
    action: str = "back"


class SelectClientCb(CallbackData, prefix="selcl"):
    client_id: int
    page: int = 0


class SelectOfferCb(CallbackData, prefix="selof"):
    offer_id: int
    page: int = 0


class SelectQTypeCb(CallbackData, prefix="sqt"):
    qtype: str


class SelectSourceTypeCb(CallbackData, prefix="sst"):
    stype: str


class PaginateCb(CallbackData, prefix="pg"):
    section: str
    page: int
    extra: int = 0   # carry-along extra id (client_id, form_id, etc.)


class QOptionCb(CallbackData, prefix="qo"):
    """Toggle a multi-choice option during user flow."""
    idx: int


class UserFlowCb(CallbackData, prefix="uf"):
    action: str    # start | skip | done | pick
    val: str = ""


class ConvCb(CallbackData, prefix="cv"):
    """Conversions / analytics dashboard."""
    section: str   # menu|clients|client|offers|offer|forms|form|refs|ref|dropoff|top|bad|export
    id: int = 0
    page: int = 0


class ConvExportCb(CallbackData, prefix="cve"):
    what: str   # funnel|dropoff|top|bad|full
    id: int = 0


class RefEditCb(CallbackData, prefix="rfe"):
    """Inline edit of a single UTM field on a ReferralSource."""
    field: str
    id: int = 0


class TodayCb(CallbackData, prefix="td"):
    """Today dashboard quick actions."""
    action: str   # refresh|new_leads|approved|site


# ── New sections ──────────────────────────────────────────────────────────────

class WizCb(CallbackData, prefix="wz"):
    """Offer-creation wizard navigation."""
    step: str   # start|sel_client|new_client|back|cancel|sel_form|new_form|
                # q_add|q_del|q_done|src_type|px_add|px_skip|px_done|
                # sel_evt|save|home|add_src
    val: str = ""   # carries id, source type, etc.


class PxCb(CallbackData, prefix="px"):
    """Pixel / tracking config actions."""
    action: str   # menu|add|view|toggle|delete|help|type|events|save_events
    id: int = 0


class RoleCb(CallbackData, prefix="rl"):
    """Bot-user / role management."""
    action: str   # list|view|toggle|delete|add|set_role|set_client
    uid: int = 0
    page: int = 0



def _add_pagination(
    builder: InlineKeyboardBuilder,
    section: str,
    page_result: PageResult,
    extra: int = 0,
) -> None:
    nav = []
    if page_result.has_prev:
        nav.append(
            builder.button(
                text="◀️ Назад",
                callback_data=PaginateCb(section=section, page=page_result.page - 1, extra=extra),
            )
        )
    if page_result.total_pages > 1:
        builder.button(
            text=f"{page_result.page + 1}/{page_result.total_pages}",
            callback_data=PaginateCb(section=section, page=page_result.page, extra=extra),
        )
    if page_result.has_next:
        builder.button(
            text="▶️ Вперёд",
            callback_data=PaginateCb(section=section, page=page_result.page + 1, extra=extra),
        )


# ══════════════════════════════════════════════════════════════════════════════
# Main menu
# ══════════════════════════════════════════════════════════════════════════════

def main_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📊 Сегодня",       callback_data=MenuCb(section="today"))
    b.button(text="📈 Конверсии",     callback_data=MenuCb(section="conv"))
    b.button(text="📥 Лиды",          callback_data=MenuCb(section="leads"))
    b.button(text="🧩 Лидформы",      callback_data=MenuCb(section="forms"))
    b.button(text="🔗 Источники",     callback_data=MenuCb(section="refs"))
    b.button(text="👥 Клиенты",       callback_data=MenuCb(section="clients"))
    b.button(text="🎯 Пиксели",       callback_data=MenuCb(section="pixels"))
    b.button(text="⚙️ Настройки",    callback_data=MenuCb(section="settings"))
    b.button(text="🚀 Создать оффер", callback_data=WizCb(step="start"))
    b.adjust(2, 2, 2, 2, 1)
    return b.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🏠 Главное меню", callback_data=MenuCb(section="main"))
    return b.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data=CancelCb(action="back"))
    return b.as_markup()


def confirm_delete_kb(target: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Да, удалить", callback_data=ConfirmCb(action="yes", target=target))
    b.button(text="❌ Нет, отмена", callback_data=ConfirmCb(action="no", target=target))
    b.adjust(2)
    return b.as_markup()


def skip_cancel_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⏭ Пропустить", callback_data=CancelCb(action="skip"))
    b.button(text="❌ Отмена", callback_data=CancelCb(action="back"))
    b.adjust(2)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Clients
# ══════════════════════════════════════════════════════════════════════════════

def clients_section_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Создать клиента", callback_data=ClientCb(action="new"))
    b.button(text="📋 Список клиентов", callback_data=ClientCb(action="list"))
    b.button(text="🔍 Найти клиента", callback_data=ClientCb(action="search"))
    b.button(text="🏠 Главное меню", callback_data=MenuCb(section="main"))
    b.adjust(1)
    return b.as_markup()


def clients_list_kb(pr: PageResult[Client]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in pr.items:
        icon = "✅" if c.status == "active" else "⏸"
        b.button(
            text=f"{icon} {c.name}",
            callback_data=ClientCb(action="view", id=c.id, page=pr.page),
        )
    b.adjust(1)
    _add_pagination(b, "clients", pr)
    b.button(text="➕ Создать", callback_data=ClientCb(action="new"))
    b.button(text="◀️ Назад", callback_data=MenuCb(section="clients"))
    b.adjust(1)
    return b.as_markup()


def client_view_kb(client: Client, page: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Изменить имя", callback_data=ClientCb(action="edit_name", id=client.id, page=page))
    b.button(text="📱 Изменить username", callback_data=ClientCb(action="edit_username", id=client.id, page=page))
    b.button(text="📝 Изменить заметки", callback_data=ClientCb(action="edit_notes", id=client.id, page=page))
    toggle_text = "⏸ Выключить" if client.status == "active" else "▶️ Включить"
    b.button(text=toggle_text, callback_data=ClientCb(action="toggle", id=client.id, page=page))
    b.button(text="🗑 Удалить", callback_data=ClientCb(action="del", id=client.id, page=page))
    b.button(text="◀️ К списку", callback_data=ClientCb(action="list", page=page))
    b.adjust(2, 2, 1, 1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Offers
# ══════════════════════════════════════════════════════════════════════════════

def offers_section_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Создать оффер", callback_data=OfferCb(action="new"))
    b.button(text="📋 Все офферы", callback_data=OfferCb(action="list"))
    b.button(text="🏠 Главное меню", callback_data=MenuCb(section="main"))
    b.adjust(1)
    return b.as_markup()


def offers_list_kb(pr: PageResult[Offer], client_id: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for o in pr.items:
        icon = "✅" if o.status == "active" else "⏸"
        b.button(
            text=f"{icon} {o.name}",
            callback_data=OfferCb(action="view", id=o.id, client_id=client_id, page=pr.page),
        )
    b.adjust(1)
    _add_pagination(b, "offers", pr, extra=client_id)
    b.button(text="➕ Создать", callback_data=OfferCb(action="new"))
    b.button(text="◀️ Назад", callback_data=MenuCb(section="offers"))
    b.adjust(1)
    return b.as_markup()


def offer_view_kb(offer: Offer, page: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Изменить название", callback_data=OfferCb(action="edit_name", id=offer.id, page=page))
    b.button(text="📄 Изменить описание", callback_data=OfferCb(action="edit_desc", id=offer.id, page=page))
    b.button(text="🌍 Изменить GEO", callback_data=OfferCb(action="edit_geo", id=offer.id, page=page))
    b.button(text="🗣 Изменить язык", callback_data=OfferCb(action="edit_lang", id=offer.id, page=page))
    toggle_text = "⏸ Выключить" if offer.status == "active" else "▶️ Включить"
    b.button(text=toggle_text, callback_data=OfferCb(action="toggle", id=offer.id, page=page))
    b.button(text="🗑 Удалить", callback_data=OfferCb(action="del", id=offer.id, page=page))
    b.button(text="◀️ К списку", callback_data=OfferCb(action="list", page=page))
    b.adjust(2, 2, 1, 1, 1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Select client / offer (for wizards)
# ══════════════════════════════════════════════════════════════════════════════

def select_client_kb(clients: List[Client], page: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in clients:
        b.button(text=c.name, callback_data=SelectClientCb(client_id=c.id, page=page))
    b.adjust(1)
    b.button(text="❌ Отмена", callback_data=CancelCb(action="back"))
    return b.as_markup()


def select_offer_kb(offers: List[Offer]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for o in offers:
        b.button(text=o.name, callback_data=SelectOfferCb(offer_id=o.id))
    b.adjust(1)
    b.button(text="❌ Отмена", callback_data=CancelCb(action="back"))
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# LeadForms
# ══════════════════════════════════════════════════════════════════════════════

def forms_section_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Создать лидформу", callback_data=FormCb(action="new"))
    b.button(text="📋 Список форм", callback_data=FormCb(action="list"))
    b.button(text="🏠 Главное меню", callback_data=MenuCb(section="main"))
    b.adjust(1)
    return b.as_markup()


def forms_list_kb(pr: PageResult[LeadForm]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for f in pr.items:
        icon = "✅" if f.status == "active" else "⏸"
        b.button(
            text=f"{icon} {f.name}",
            callback_data=FormCb(action="view", id=f.id, page=pr.page),
        )
    b.adjust(1)
    _add_pagination(b, "forms", pr)
    b.button(text="➕ Создать", callback_data=FormCb(action="new"))
    b.button(text="◀️ Назад", callback_data=MenuCb(section="forms"))
    b.adjust(1)
    return b.as_markup()


def form_view_kb(form: LeadForm, page: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Название", callback_data=FormEditCb(field="name", id=form.id))
    b.button(text="👋 Welcome текст", callback_data=FormEditCb(field="welcome_text", id=form.id))
    b.button(text="✅ Success текст", callback_data=FormEditCb(field="success_text", id=form.id))
    b.button(text="🗣 Язык", callback_data=FormEditCb(field="language", id=form.id))
    b.button(text="➕ Добавить вопрос", callback_data=QuestionCb(action="new", form_id=form.id))
    b.button(text="🧩 Вопросы", callback_data=QuestionCb(action="list", form_id=form.id))
    b.button(text="🔗 Создать рефку", callback_data=RefCb(action="new", form_id=form.id))
    b.button(text="📊 Статистика", callback_data=StatsCb(action="form", id=form.id))
    b.button(text="📥 Лиды формы", callback_data=LeadCb(action="by_form", id=form.id))
    b.button(text="📤 Экспорт лидов", callback_data=ExportCb(action="form", fmt=str(form.id)))
    toggle_text = "⏸ Выключить" if form.status == "active" else "▶️ Включить"
    b.button(text=toggle_text, callback_data=FormCb(action="toggle", id=form.id, page=page))
    b.button(text="🗑 Удалить форму", callback_data=FormCb(action="del", id=form.id, page=page))
    b.button(text="◀️ К списку форм", callback_data=FormCb(action="list", page=page))
    b.adjust(2, 2, 2, 2, 2, 2, 1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Questions
# ══════════════════════════════════════════════════════════════════════════════

def question_type_kb() -> InlineKeyboardMarkup:
    types = [
        ("📝 Текст", "text"),
        ("☎️ Телефон", "phone"),
        ("👤 Telegram username", "telegram_username"),
        ("🔢 Число", "number"),
        ("📅 Дата", "date"),
        ("1️⃣ Один вариант", "single_choice"),
        ("☑️ Несколько вариантов", "multi_choice"),
        ("💬 Комментарий", "comment"),
    ]
    b = InlineKeyboardBuilder()
    for label, qtype in types:
        b.button(text=label, callback_data=SelectQTypeCb(qtype=qtype))
    b.button(text="❌ Отмена", callback_data=CancelCb(action="back"))
    b.adjust(2, 2, 2, 2, 1)
    return b.as_markup()


def required_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="❗ Обязательный", callback_data=CancelCb(action="required_yes"))
    b.button(text="⬜ Необязательный", callback_data=CancelCb(action="required_no"))
    b.adjust(2)
    return b.as_markup()


def questions_list_kb(questions: List[LeadFormQuestion], form_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for q in questions:
        req = "❗" if q.is_required else "⬜"
        b.button(
            text=f"{req} {q.position}. {q.question_text[:30]}",
            callback_data=QuestionCb(action="view", id=q.id, form_id=form_id),
        )
    b.adjust(1)
    b.button(text="➕ Добавить вопрос", callback_data=QuestionCb(action="new", form_id=form_id))
    b.button(text="◀️ Назад к форме", callback_data=FormCb(action="view", id=form_id))
    b.adjust(1)
    return b.as_markup()


def question_view_kb(question: LeadFormQuestion) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Изменить текст", callback_data=QuestionCb(action="edit_text", id=question.id, form_id=question.form_id))
    b.button(text="⬆️ Вверх", callback_data=QuestionCb(action="move_up", id=question.id, form_id=question.form_id))
    b.button(text="⬇️ Вниз", callback_data=QuestionCb(action="move_down", id=question.id, form_id=question.form_id))
    b.button(text="🗑 Удалить", callback_data=QuestionCb(action="del", id=question.id, form_id=question.form_id))
    b.button(text="◀️ К вопросам", callback_data=QuestionCb(action="list", form_id=question.form_id))
    b.adjust(1, 2, 1, 1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Referral Sources
# ══════════════════════════════════════════════════════════════════════════════

def source_type_kb() -> InlineKeyboardMarkup:
    types = [
        ("📘 Facebook", "facebook"),
        ("📷 Instagram", "instagram"),
        ("🎵 TikTok", "tiktok"),
        ("✈️ Telegram", "telegram"),
        ("🔍 Google", "google"),
        ("✍️ Manual", "manual"),
        ("❓ Other", "other"),
    ]
    b = InlineKeyboardBuilder()
    for label, stype in types:
        b.button(text=label, callback_data=SelectSourceTypeCb(stype=stype))
    b.button(text="❌ Отмена", callback_data=CancelCb(action="back"))
    b.adjust(2, 2, 2, 1, 1)
    return b.as_markup()


def refs_list_kb(refs: List[ReferralSource], form_id: int, page: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for r in refs:
        icon = "✅" if r.status == "active" else "⏸"
        b.button(
            text=f"{icon} {r.name}",
            callback_data=RefCb(action="view", id=r.id, form_id=form_id, page=page),
        )
    b.adjust(1)
    b.button(text="➕ Создать рефку", callback_data=RefCb(action="new", form_id=form_id))
    b.button(text="◀️ Назад к форме", callback_data=FormCb(action="view", id=form_id))
    b.adjust(1)
    return b.as_markup()


def ref_view_kb(ref: ReferralSource) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Изменить название", callback_data=RefCb(action="edit_name", id=ref.id, form_id=ref.form_id))
    b.button(text="📊 Статистика", callback_data=StatsCb(action="ref", id=ref.id))
    b.button(text="📈 Конверсии", callback_data=ConvCb(section="ref", id=ref.id))
    b.button(text="✏️ UTM поля", callback_data=RefCb(action="utm_menu", id=ref.id, form_id=ref.form_id))
    toggle_text = "⏸ Выключить" if ref.status == "active" else "▶️ Включить"
    b.button(text=toggle_text, callback_data=RefCb(action="toggle", id=ref.id, form_id=ref.form_id))
    b.button(text="🗑 Удалить", callback_data=RefCb(action="del", id=ref.id, form_id=ref.form_id))
    b.button(text="◀️ К рефкам", callback_data=RefCb(action="list", form_id=ref.form_id))
    b.adjust(2, 2, 2, 1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Leads
# ══════════════════════════════════════════════════════════════════════════════

def leads_section_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📋 Все лиды", callback_data=LeadCb(action="list"))
    b.button(text="🔍 Фильтр", callback_data=LeadCb(action="filter"))
    b.button(text="🗑 Сбросить фильтр", callback_data=LeadCb(action="reset_filter"))
    b.button(text="🏠 Главное меню", callback_data=MenuCb(section="main"))
    b.adjust(1)
    return b.as_markup()


def leads_list_kb(pr: PageResult[Lead], has_filter: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for lead in pr.items:
        from models.lead import LEAD_STATUS_LABELS
        status_label = LEAD_STATUS_LABELS.get(lead.status, lead.status)
        name = lead.first_name or lead.telegram_username or str(lead.telegram_user_id)
        b.button(
            text=f"{status_label} — {name}",
            callback_data=LeadCb(action="view", id=lead.id, page=pr.page),
        )
    b.adjust(1)
    _add_pagination(b, "leads", pr)
    if has_filter:
        b.button(text="🗑 Сбросить фильтр", callback_data=LeadCb(action="reset_filter"))
    b.button(text="◀️ Назад", callback_data=MenuCb(section="leads"))
    b.adjust(1)
    return b.as_markup()


def lead_view_kb(lead: Lead, page: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔄 Сменить статус", callback_data=LeadCb(action="change_status", id=lead.id, page=page))
    b.button(text="📝 Добавить заметку", callback_data=LeadCb(action="add_note", id=lead.id, page=page))
    b.button(text="◀️ К списку", callback_data=LeadCb(action="list", page=page))
    b.adjust(2, 1)
    return b.as_markup()


def lead_status_kb(lead_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for status, label in LEAD_STATUS_LABELS.items():
        b.button(text=label, callback_data=LeadStatusCb(lead_id=lead_id, status=status))
    b.button(text="◀️ Назад", callback_data=LeadCb(action="view", id=lead_id))
    b.adjust(2, 2, 2, 1)
    return b.as_markup()


def lead_filter_kb(current: dict) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    cl_label = f"Клиент: {current.get('client_name', 'Все')}"
    of_label = f"Оффер: {current.get('offer_name', 'Все')}"
    fm_label = f"Форма: {current.get('form_name', 'Все')}"
    st_label = f"Статус: {current.get('status', 'Все')}"
    b.button(text=cl_label, callback_data=LeadFilterCb(field="client_id"))
    b.button(text=of_label, callback_data=LeadFilterCb(field="offer_id"))
    b.button(text=fm_label, callback_data=LeadFilterCb(field="form_id"))
    b.button(text=st_label, callback_data=LeadFilterCb(field="status"))
    b.button(text="📅 Дата от", callback_data=LeadFilterCb(field="date_from"))
    b.button(text="📅 Дата до", callback_data=LeadFilterCb(field="date_to"))
    b.button(text="✅ Применить", callback_data=LeadCb(action="list"))
    b.button(text="🗑 Сбросить всё", callback_data=LeadCb(action="reset_filter"))
    b.button(text="◀️ Назад", callback_data=MenuCb(section="leads"))
    b.adjust(2, 2, 2, 2, 1)
    return b.as_markup()


def filter_status_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for status, label in LEAD_STATUS_LABELS.items():
        b.button(text=label, callback_data=LeadFilterCb(field="status", val=status))
    b.button(text="🔄 Все статусы", callback_data=LeadFilterCb(field="status", val=""))
    b.button(text="◀️ Назад", callback_data=LeadCb(action="filter"))
    b.adjust(2, 2, 2, 1, 1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Statistics
# ══════════════════════════════════════════════════════════════════════════════

def stats_section_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🌍 Общая статистика", callback_data=StatsCb(action="global"))
    b.button(text="👥 По клиенту", callback_data=StatsCb(action="select_client"))
    b.button(text="📦 По офферу", callback_data=StatsCb(action="select_offer"))
    b.button(text="📝 По форме", callback_data=StatsCb(action="select_form"))
    b.button(text="🏠 Главное меню", callback_data=MenuCb(section="main"))
    b.adjust(1)
    return b.as_markup()


def select_client_for_stats_kb(clients: List[Client]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in clients:
        b.button(text=c.name, callback_data=StatsCb(action="client", id=c.id))
    b.button(text="◀️ Назад", callback_data=MenuCb(section="stats"))
    b.adjust(1)
    return b.as_markup()


def select_offer_for_stats_kb(offers: List[Offer]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for o in offers:
        b.button(text=o.name, callback_data=StatsCb(action="offer", id=o.id))
    b.button(text="◀️ Назад", callback_data=MenuCb(section="stats"))
    b.adjust(1)
    return b.as_markup()


def select_form_for_stats_kb(forms: List[LeadForm]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for f in forms:
        b.button(text=f.name, callback_data=StatsCb(action="form", id=f.id))
    b.button(text="◀️ Назад", callback_data=MenuCb(section="stats"))
    b.adjust(1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Export
# ══════════════════════════════════════════════════════════════════════════════

def export_section_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📊 Экспорт в CSV", callback_data=ExportCb(action="start", fmt="csv"))
    b.button(text="📗 Экспорт в XLSX", callback_data=ExportCb(action="start", fmt="xlsx"))
    b.button(text="🏠 Главное меню", callback_data=MenuCb(section="main"))
    b.adjust(2, 1)
    return b.as_markup()


def export_filter_kb(fmt: str, current: dict) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    cl_label = f"Клиент: {current.get('client_name', 'Все')}"
    of_label = f"Оффер: {current.get('offer_name', 'Все')}"
    fm_label = f"Форма: {current.get('form_name', 'Все')}"
    b.button(text=cl_label, callback_data=ExportCb(action="filter_client", fmt=fmt))
    b.button(text=of_label, callback_data=ExportCb(action="filter_offer", fmt=fmt))
    b.button(text=fm_label, callback_data=ExportCb(action="filter_form", fmt=fmt))
    b.button(text="✅ Скачать", callback_data=ExportCb(action="download", fmt=fmt))
    b.button(text="◀️ Назад", callback_data=MenuCb(section="export"))
    b.adjust(1, 1, 1, 1, 1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# UTM / Referral edit
# ══════════════════════════════════════════════════════════════════════════════

def ref_utm_kb(ref_id: int, form_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🌐 Traffic source", callback_data=RefEditCb(field="traffic_source", id=ref_id))
    b.button(text="📣 Campaign", callback_data=RefEditCb(field="campaign_name", id=ref_id))
    b.button(text="💳 Ad Account", callback_data=RefEditCb(field="ad_account", id=ref_id))
    b.button(text="🎨 Creative", callback_data=RefEditCb(field="creative_name", id=ref_id))
    b.button(text="📍 Placement", callback_data=RefEditCb(field="placement", id=ref_id))
    b.button(text="🌍 GEO", callback_data=RefEditCb(field="utm_geo", id=ref_id))
    b.button(text="◀️ Назад", callback_data=RefCb(action="view", id=ref_id, form_id=form_id))
    b.adjust(2, 2, 2, 1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Conversions / Analytics keyboards
# ══════════════════════════════════════════════════════════════════════════════

def conversions_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="👥 По клиентам", callback_data=ConvCb(section="clients"))
    b.button(text="📦 По офферам", callback_data=ConvCb(section="offers"))
    b.button(text="📝 По формам", callback_data=ConvCb(section="forms"))
    b.button(text="🔗 По источникам", callback_data=ConvCb(section="refs"))
    b.button(text="❓ Drop-off по вопросам", callback_data=ConvCb(section="dropoff"))
    b.button(text="🏆 Топ источники", callback_data=ConvCb(section="top"))
    b.button(text="⚠️ Плохие источники", callback_data=ConvCb(section="bad"))
    b.button(text="📤 Экспорт аналитики", callback_data=ConvCb(section="export"))
    b.button(text="🏠 Главное меню", callback_data=MenuCb(section="main"))
    b.adjust(2, 2, 2, 2, 1)
    return b.as_markup()


def conv_back_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="◀️ К конверсиям", callback_data=ConvCb(section="menu"))
    return b.as_markup()


def conv_ref_actions_kb(ref_id: int, form_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📥 Лиды источника", callback_data=LeadCb(action="list"))
    b.button(text="❓ Drop-off формы", callback_data=ConvCb(section="dropoff", id=form_id))
    b.button(text="📤 Экспорт", callback_data=ConvExportCb(what="funnel", id=ref_id))
    b.button(text="◀️ К источникам", callback_data=ConvCb(section="refs"))
    b.adjust(2, 1, 1)
    return b.as_markup()


def conv_form_actions_kb(form_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="❓ Drop-off", callback_data=ConvCb(section="dropoff", id=form_id))
    b.button(text="📤 Экспорт drop-off", callback_data=ConvExportCb(what="dropoff", id=form_id))
    b.button(text="◀️ К формам", callback_data=ConvCb(section="forms"))
    b.adjust(2, 1)
    return b.as_markup()


def conv_export_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📊 Воронка по источникам", callback_data=ConvExportCb(what="funnel"))
    b.button(text="🏆 Топ источники", callback_data=ConvExportCb(what="top"))
    b.button(text="⚠️ Плохие источники", callback_data=ConvExportCb(what="bad"))
    b.button(text="📦 Полный отчёт", callback_data=ConvExportCb(what="full"))
    b.button(text="◀️ Назад", callback_data=ConvCb(section="menu"))
    b.adjust(1)
    return b.as_markup()


def conv_select_form_for_dropoff_kb(forms: List[LeadForm]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for f in forms:
        b.button(text=f.name, callback_data=ConvCb(section="dropoff", id=f.id))
    b.adjust(1)
    b.button(text="◀️ Назад", callback_data=ConvCb(section="menu"))
    return b.as_markup()


def conv_select_client_kb(clients: List[Client]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in clients:
        b.button(text=c.name, callback_data=ConvCb(section="client", id=c.id))
    b.adjust(1)
    b.button(text="◀️ Назад", callback_data=ConvCb(section="menu"))
    return b.as_markup()


def conv_select_offer_kb(offers: List[Offer]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for o in offers:
        b.button(text=o.name, callback_data=ConvCb(section="offer", id=o.id))
    b.adjust(1)
    b.button(text="◀️ Назад", callback_data=ConvCb(section="menu"))
    return b.as_markup()


def conv_select_form_kb(forms: List[LeadForm]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for f in forms:
        b.button(text=f.name, callback_data=ConvCb(section="form", id=f.id))
    b.adjust(1)
    b.button(text="◀️ Назад", callback_data=ConvCb(section="menu"))
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# "📊 Сегодня" dashboard keyboards
# ══════════════════════════════════════════════════════════════════════════════

def today_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔥 Топ источники",   callback_data=ConvCb(section="top"))
    b.button(text="⚠️ Плохие",          callback_data=ConvCb(section="bad"))
    b.button(text="📥 Новые лиды",       callback_data=LeadCb(action="list"))
    b.button(text="✅ Approved",         callback_data=LeadCb(action="list"))
    b.button(text="📈 Воронка",          callback_data=ConvCb(section="menu"))
    b.button(text="📤 Экспорт",          callback_data=ConvCb(section="export"))
    b.button(text="🔄 Обновить",         callback_data=TodayCb(action="refresh"))
    b.button(text="🏠 Главное меню",     callback_data=MenuCb(section="main"))
    b.adjust(2, 2, 2, 1, 1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Global sources list with mini-metrics
# ══════════════════════════════════════════════════════════════════════════════

def _source_quality_icon(leads: int, approved: int, starts: int) -> str:
    """Return colour dot based on approve rate and data volume."""
    if starts < 5:
        return "⚫"   # not enough data
    if not leads:
        return "🔴"
    rate = approved / leads * 100
    if rate >= 15:
        return "🟢"
    if rate >= 5:
        return "🟡"
    return "🔴"


def refs_global_kb(
    refs_stats: List[tuple],  # list of (ReferralSource, leads, approved, starts)
) -> InlineKeyboardMarkup:
    """
    refs_stats: list of (ref, leads_today, approved_today, starts_today)
    Produces buttons like:  🟢 fb12_story02 | 38L / 7A / 18%
    """
    b = InlineKeyboardBuilder()
    for ref, leads, approved, starts in refs_stats:
        icon = _source_quality_icon(leads, approved, starts)
        rate = f"{round(approved / leads * 100)}%" if leads else "0%"
        label = f"{ref.name[:18]} | {leads}L / {approved}A / {rate}"
        b.button(
            text=f"{icon} {label}",
            callback_data=ConvCb(section="ref", id=ref.id),
        )
    b.button(text="🔥 Топ",          callback_data=ConvCb(section="top"))
    b.button(text="⚠️ Плохие",        callback_data=ConvCb(section="bad"))
    b.button(text="📤 Экспорт",        callback_data=ConvExportCb(what="funnel"))
    b.button(text="🏠 Главное меню",   callback_data=MenuCb(section="main"))
    n = len(refs_stats)
    rows = [1] * n + [2, 1, 1]
    b.adjust(*rows)
    return b.as_markup()


def ref_global_card_kb(ref: ReferralSource) -> InlineKeyboardMarkup:
    """Action buttons on a source card viewed from the global sources list."""
    b = InlineKeyboardBuilder()
    b.button(text="📥 Лиды",          callback_data=LeadCb(action="list"))
    b.button(text="❓ Drop-off",       callback_data=ConvCb(section="dropoff", id=ref.form_id))
    b.button(text="📤 Экспорт",        callback_data=ConvExportCb(what="funnel", id=ref.id))
    toggle_text = "⏸ Выключить" if ref.status == "active" else "▶️ Включить"
    b.button(text=toggle_text,         callback_data=RefCb(action="toggle", id=ref.id, form_id=ref.form_id))
    b.button(text="✏️ UTM поля",       callback_data=RefCb(action="utm_menu", id=ref.id, form_id=ref.form_id))
    b.button(text="◀️ К источникам",   callback_data=MenuCb(section="refs"))
    b.adjust(2, 1, 2, 1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Settings
# ══════════════════════════════════════════════════════════════════════════════

def settings_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="👥 Пользователи и роли", callback_data=RoleCb(action="list"))
    b.button(text="🏠 Главное меню",        callback_data=MenuCb(section="main"))
    b.adjust(1)
    return b.as_markup()


def roles_list_kb(users: list, page: int = 0, total: int = 0) -> InlineKeyboardMarkup:
    _ROLE_ICONS = {
        "super_admin": "👑",
        "client_admin": "👤",
        "client_viewer": "👁",
        "manager": "📞",
    }
    b = InlineKeyboardBuilder()
    for u in users:
        icon = _ROLE_ICONS.get(u.role, "❓")
        active = "✅" if u.is_active else "⏸"
        name = (u.telegram_username or str(u.telegram_user_id))[:20]
        b.button(
            text=f"{active}{icon} {name}",
            callback_data=RoleCb(action="view", uid=u.id),
        )
    b.adjust(1)
    b.button(text="➕ Добавить пользователя", callback_data=RoleCb(action="add"))
    b.button(text="⬅️ Настройки",             callback_data=MenuCb(section="settings"))
    b.adjust(1)
    return b.as_markup()


def role_user_view_kb(uid: int, is_active: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    toggle = "⏸ Отключить" if is_active else "▶️ Включить"
    b.button(text=toggle,          callback_data=RoleCb(action="toggle", uid=uid))
    b.button(text="🔄 Сменить роль", callback_data=RoleCb(action="set_role", uid=uid))
    b.button(text="🗑 Удалить",     callback_data=RoleCb(action="delete", uid=uid))
    b.button(text="◀️ Назад",       callback_data=RoleCb(action="list"))
    b.adjust(2, 1, 1)
    return b.as_markup()


def role_select_kb(uid: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    roles = [
        ("👤 Client Admin",   "client_admin"),
        ("👁 Client Viewer",  "client_viewer"),
        ("📞 Manager",        "manager"),
    ]
    for label, role in roles:
        b.button(text=label, callback_data=RoleCb(action="set_role", uid=uid, page=0))
    b.button(text="❌ Отмена", callback_data=RoleCb(action="list"))
    b.adjust(1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Offer wizard keyboards
# ══════════════════════════════════════════════════════════════════════════════

def wiz_clients_kb(clients: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Новый клиент", callback_data=WizCb(step="new_client"))
    for c in clients:
        b.button(text=c.name, callback_data=WizCb(step="sel_client", val=str(c.id)))
    b.adjust(1)
    b.button(text="❌ Отмена", callback_data=WizCb(step="cancel"))
    b.adjust(1)
    return b.as_markup()


def wiz_forms_kb(forms: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Новая форма", callback_data=WizCb(step="new_form"))
    for f in forms:
        b.button(text=f.name, callback_data=WizCb(step="sel_form", val=str(f.id)))
    b.adjust(1)
    b.button(text="⬅️ Назад", callback_data=WizCb(step="back"))
    b.button(text="❌ Отмена", callback_data=WizCb(step="cancel"))
    b.adjust(1)
    return b.as_markup()


def wiz_questions_kb(questions: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for i, q in enumerate(questions):
        b.button(
            text=f"🗑 {i+1}. {q['text'][:22]}",
            callback_data=WizCb(step="q_del", val=str(i)),
        )
    b.button(text="➕ Добавить вопрос", callback_data=WizCb(step="q_add"))
    b.button(text="✅ Готово",           callback_data=WizCb(step="q_done"))
    b.button(text="⬅️ Назад",           callback_data=WizCb(step="back"))
    b.button(text="❌ Отмена",           callback_data=WizCb(step="cancel"))
    b.adjust(1)
    return b.as_markup()


def wiz_question_type_kb() -> InlineKeyboardMarkup:
    types = [
        ("📝 Текст",       "text"),
        ("☎️ Телефон",     "phone"),
        ("👤 Username",    "telegram_username"),
        ("🔢 Число",       "number"),
        ("📅 Дата",        "date"),
        ("1️⃣ Один вариант", "single_choice"),
        ("☑️ Несколько",   "multi_choice"),
    ]
    b = InlineKeyboardBuilder()
    for label, qtype in types:
        b.button(text=label, callback_data=WizCb(step="q_type", val=qtype))
    b.button(text="❌ Отмена", callback_data=WizCb(step="q_cancel"))
    b.adjust(2, 2, 2, 1, 1)
    return b.as_markup()


def wiz_source_type_kb() -> InlineKeyboardMarkup:
    sources = [
        ("📘 Facebook",  "facebook"),
        ("📷 Instagram", "instagram"),
        ("🎵 TikTok",    "tiktok"),
        ("✈️ Telegram",  "telegram"),
        ("🔍 Google",    "google"),
        ("❓ Другое",    "other"),
    ]
    b = InlineKeyboardBuilder()
    for label, val in sources:
        b.button(text=label, callback_data=WizCb(step="src_type", val=val))
    b.adjust(2, 2, 2)
    b.button(text="⬅️ Назад", callback_data=WizCb(step="back"))
    b.button(text="❌ Отмена", callback_data=WizCb(step="cancel"))
    b.adjust(2, 2, 2, 2)
    return b.as_markup()


def wiz_pixel_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🎯 Добавить пиксель", callback_data=WizCb(step="px_add"))
    b.button(text="⏭ Пропустить",        callback_data=WizCb(step="px_skip"))
    b.button(text="⬅️ Назад",            callback_data=WizCb(step="back"))
    b.button(text="❌ Отмена",            callback_data=WizCb(step="cancel"))
    b.adjust(1, 1, 2)
    return b.as_markup()


def wiz_pixel_type_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📘 Meta Pixel",    callback_data=WizCb(step="px_type", val="meta"))
    b.button(text="🔵 Google Tag",    callback_data=WizCb(step="px_type", val="google"))
    b.button(text="🎵 TikTok Pixel",  callback_data=WizCb(step="px_type", val="tiktok"))
    b.button(text="✈️ Telegram only", callback_data=WizCb(step="px_type", val="telegram"))
    b.button(text="⬅️ Назад",        callback_data=WizCb(step="back"))
    b.adjust(1, 1, 1, 1, 1)
    return b.as_markup()


def wiz_pixel_events_kb(selected: list) -> InlineKeyboardMarkup:
    from models.pixel import PIXEL_EVENTS_ALL
    b = InlineKeyboardBuilder()
    for evt in PIXEL_EVENTS_ALL:
        check = "✅" if evt in selected else "⬜"
        b.button(text=f"{check} {evt}", callback_data=WizCb(step="sel_evt", val=evt))
    b.button(text="💾 Сохранить", callback_data=WizCb(step="px_done"))
    b.button(text="⬅️ Назад",    callback_data=WizCb(step="back"))
    b.adjust(1)
    return b.as_markup()


def wiz_done_kb(form_id: int = 0, ref_id: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📊 Статистика",   callback_data=MenuCb(section="today"))
    b.button(text="📥 Лиды",         callback_data=MenuCb(section="leads"))
    b.button(text="➕ Ещё источник",  callback_data=WizCb(step="add_src", val=str(form_id)))
    b.button(text="🏠 Главное меню", callback_data=MenuCb(section="main"))
    b.adjust(2, 1, 1)
    return b.as_markup()


# ══════════════════════════════════════════════════════════════════════════════
# Pixel management keyboards
# ══════════════════════════════════════════════════════════════════════════════

def pixels_menu_kb(pixels: list) -> InlineKeyboardMarkup:
    from models.pixel import PIXEL_TYPE_ICONS
    b = InlineKeyboardBuilder()
    for px in pixels:
        icon = "✅" if px.is_active else "⏸"
        type_icon = PIXEL_TYPE_ICONS.get(px.pixel_type, "📡")
        b.button(
            text=f"{icon}{type_icon} {px.name[:22]}",
            callback_data=PxCb(action="view", id=px.id),
        )
    b.adjust(1)
    b.button(text="➕ Добавить пиксель",    callback_data=PxCb(action="add"))
    b.button(text="❔ Как это работает?",   callback_data=PxCb(action="help"))
    b.button(text="🏠 Главное меню",        callback_data=MenuCb(section="main"))
    n = len(pixels)
    b.adjust(*([1] * n), 1, 1, 1)
    return b.as_markup()


def pixel_view_kb(px_id: int, is_active: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    toggle = "⏸ Выключить" if is_active else "▶️ Включить"
    b.button(text=toggle,               callback_data=PxCb(action="toggle", id=px_id))
    b.button(text="📌 Изменить события", callback_data=PxCb(action="events", id=px_id))
    b.button(text="🗑 Удалить",          callback_data=PxCb(action="delete", id=px_id))
    b.button(text="◀️ К пикселям",       callback_data=MenuCb(section="pixels"))
    b.adjust(2, 1, 1)
    return b.as_markup()


def pixel_type_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📘 Meta Pixel",    callback_data=PxCb(action="type", id=1))
    b.button(text="🔵 Google Tag",    callback_data=PxCb(action="type", id=2))
    b.button(text="🎵 TikTok Pixel",  callback_data=PxCb(action="type", id=3))
    b.button(text="✈️ Telegram only", callback_data=PxCb(action="type", id=4))
    b.button(text="◀️ Назад",         callback_data=MenuCb(section="pixels"))
    b.adjust(1)
    return b.as_markup()


def pixel_scope_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🌐 Глобально (все)", callback_data=PxCb(action="scope", id=0))
    b.button(text="👥 К клиенту",       callback_data=PxCb(action="scope", id=1))
    b.button(text="📦 К офферу",        callback_data=PxCb(action="scope", id=2))
    b.button(text="📝 К форме",         callback_data=PxCb(action="scope", id=3))
    b.button(text="🔗 К источнику",     callback_data=PxCb(action="scope", id=4))
    b.button(text="◀️ Назад",           callback_data=PxCb(action="add"))
    b.adjust(1)
    return b.as_markup()


def pixel_events_kb(selected: list) -> InlineKeyboardMarkup:
    from models.pixel import PIXEL_EVENTS_ALL
    b = InlineKeyboardBuilder()
    for evt in PIXEL_EVENTS_ALL:
        check = "✅" if evt in selected else "⬜"
        b.button(
            text=f"{check} {evt}",
            callback_data=PxCb(action="save_events", id=hash(evt) & 0x7FFFFFFF),
        )
    b.button(text="💾 Сохранить", callback_data=PxCb(action="save_events", id=0))
    b.button(text="◀️ Назад",     callback_data=MenuCb(section="pixels"))
    b.adjust(1)
    return b.as_markup()
