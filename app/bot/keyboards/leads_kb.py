from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def leads_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🆕 Сегодня", callback_data="leads:today")],
            [InlineKeyboardButton(text="⚠️ Ошибки доставки", callback_data="leads:errors")],
            [InlineKeyboardButton(text="📋 Все лиды", callback_data="leads:all")],
            [
                InlineKeyboardButton(text="🔍 По клиенту", callback_data="leads:by_client"),
                InlineKeyboardButton(text="📋 По FB форме", callback_data="leads:by_form"),
            ],
            [InlineKeyboardButton(text="📤 Экспорт", callback_data="leads:export")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main:menu")],
        ]
    )


def lead_card_kb(lead_id: int, client_id: int | None = None, form_id: int | None = None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="🔁 Повторить доставку", callback_data=f"leads:retry:{lead_id}")]]
    row = []
    if client_id:
        row.append(InlineKeyboardButton(text="👥 Открыть клиента", callback_data=f"clients:card:{client_id}"))
    if form_id:
        row.append(InlineKeyboardButton(text="📋 Открыть форму", callback_data=f"fbforms:card:{form_id}"))
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="📄 Raw data", callback_data=f"leads:raw:{lead_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ К лидам", callback_data="leads:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
