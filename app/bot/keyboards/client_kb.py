from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def client_cabinet_kb(funnels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for form in funnels:
        builder.row(InlineKeyboardButton(
            text=form.form_name,
            callback_data=f"cl:funnel:{form.id}",
        ))
    return builder.as_markup()


def client_funnel_kb(form_id: int, page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏰ Сегодня по часам", callback_data=f"cl:stats_today:{form_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="\U0001f4c5 7 дней", callback_data=f"cl:stats_7d:{form_id}"),
        InlineKeyboardButton(text="\U0001f4c6 30 дней", callback_data=f"cl:stats_30d:{form_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="\U0001f4e6 Архив лидов", callback_data=f"cl:archive:{form_id}:0"),
    )
    builder.row(
        InlineKeyboardButton(text="\u2b05 К воронкам", callback_data="cl:cabinet"),
    )
    return builder.as_markup()


def client_archive_kb(form_id: int, page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    nav: list[InlineKeyboardButton] = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="⬅ Назад", callback_data=f"cl:archive:{form_id}:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="Вперёд ➡", callback_data=f"cl:archive:{form_id}:{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="\u2b05 Назад", callback_data=f"cl:funnel:{form_id}"))
    return builder.as_markup()


def client_stats_back_kb(form_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="\u2b05 Назад", callback_data=f"cl:funnel:{form_id}"))
    return builder.as_markup()


def client_no_funnels_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="\U0001f504 Обновить",
        callback_data="cl:cabinet",
    ))
    return builder.as_markup()
