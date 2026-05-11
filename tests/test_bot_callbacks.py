from types import SimpleNamespace

from aiogram.types import InlineKeyboardMarkup

from app.bot.keyboards.client_kb import (
    client_archive_kb,
    client_cabinet_kb,
    client_funnel_kb,
    client_no_funnels_kb,
    client_stats_back_kb,
)
from app.bot.keyboards.funnel_kb import (
    funnel_card_kb,
    funnel_created_kb,
    funnel_join_notify_kb,
    funnel_list_kb,
    funnel_sendold_menu_kb,
    funnel_stats_kb,
    recipients_list_kb,
    sheet_name_kb,
    skip_kb,
)
from app.bot.keyboards.leads_kb import lead_card_kb, leads_list_kb, leads_menu_kb
from app.bot.keyboards.main_kb import main_menu_kb
from app.bot.keyboards.prelands_kb import preland_card_kb, prelands_list_kb, prelands_menu_kb
from app.bot.keyboards.stats_kb import stats_menu_kb


def _callbacks(markup: InlineKeyboardMarkup) -> list[str]:
    values: list[str] = []
    for row in markup.inline_keyboard:
        for button in row:
            if button.callback_data:
                values.append(button.callback_data)
    return values


def test_keyboard_callbacks_are_short_and_use_current_prefixes():
    form = SimpleNamespace(id=123, status="active", form_name="Main funnel", client_label=None)
    recipient = SimpleNamespace(
        id=456,
        first_name="Client",
        telegram_username=None,
        telegram_user_id=777,
        status="active",
    )
    lead = SimpleNamespace(id=789, full_name="Anna", phone="+10000000000")
    preland = SimpleNamespace(id=321, status="active", name="Preland")

    markups = [
        main_menu_kb(),
        funnel_list_kb([form]),
        funnel_card_kb(form.id, True),
        funnel_created_kb(form.id),
        funnel_join_notify_kb(form.id, recipient.id),
        funnel_sendold_menu_kb([recipient], form.id),
        funnel_stats_kb(form.id),
        recipients_list_kb([recipient], form.id),
        sheet_name_kb(),
        skip_kb(),
        leads_menu_kb(),
        lead_card_kb(lead.id),
        leads_list_kb([lead]),
        prelands_menu_kb(),
        preland_card_kb(preland.id),
        prelands_list_kb([preland]),
        stats_menu_kb(),
        client_cabinet_kb([form]),
        client_funnel_kb(form.id),
        client_archive_kb(form.id, page=1, has_prev=True, has_next=True),
        client_stats_back_kb(form.id),
        client_no_funnels_kb(),
    ]

    callbacks = [callback for markup in markups for callback in _callbacks(markup)]
    allowed_prefixes = ("main:", "funnel:", "wizard:", "leads:", "prelands:", "pl:", "stats:", "settings:", "cl:")

    assert callbacks
    assert all(len(callback.encode("utf-8")) <= 64 for callback in callbacks)
    assert all(callback.startswith(allowed_prefixes) for callback in callbacks)
    assert not any(callback.startswith(("client:", "clients:", "forms:")) for callback in callbacks)
