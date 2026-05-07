"""Inline keyboards used during the user lead-form flow."""
from __future__ import annotations

import json
from typing import List

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.admin_kb import UserFlowCb, QOptionCb


def start_form_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🚀 Начать", callback_data=UserFlowCb(action="start"))
    return b.as_markup()


def single_choice_kb(options: List[str]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for idx, opt in enumerate(options):
        b.button(text=opt, callback_data=UserFlowCb(action="pick", val=opt))
    b.adjust(1)
    return b.as_markup()


def multi_choice_kb(options: List[str], selected: List[int]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for idx, opt in enumerate(options):
        prefix = "✅ " if idx in selected else "⬜ "
        b.button(text=f"{prefix}{opt}", callback_data=QOptionCb(idx=idx))
    b.button(text="✔️ Готово", callback_data=UserFlowCb(action="done"))
    b.adjust(1)
    return b.as_markup()


def skip_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⏭ Пропустить", callback_data=UserFlowCb(action="skip"))
    return b.as_markup()
