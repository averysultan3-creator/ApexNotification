from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def leads_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆕 Сегодня", callback_data="leads:today")],
        [InlineKeyboardButton(text="⚠️ Ошибки", callback_data="leads:errors")],
        [InlineKeyboardButton(text="📋 Последние 20", callback_data="leads:last20")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main:menu")],
    ])


def lead_card_kb(lead_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Повторить отправку", callback_data=f"leads:retry:{lead_id}")],
        [InlineKeyboardButton(text="📄 Raw данные", callback_data=f"leads:raw:{lead_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="leads:last20")],
    ])


def leads_list_kb(leads: list, back_cb: str = "leads:menu") -> InlineKeyboardMarkup:
    buttons = []
    for lead in leads:
        label = f"#{lead.id} {lead.full_name or '—'} {lead.phone or ''}".strip()
        buttons.append([InlineKeyboardButton(text=label[:50], callback_data=f"leads:card:{lead.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
