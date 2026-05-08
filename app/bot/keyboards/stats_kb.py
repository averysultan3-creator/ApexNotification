from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def stats_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Лиды сегодня", callback_data="stats:leads_today")],
        [InlineKeyboardButton(text="📋 По FB формам", callback_data="stats:by_form")],
        [InlineKeyboardButton(text="👥 По клиентам", callback_data="stats:by_client")],
        [InlineKeyboardButton(text="🌐 Prelands сегодня", callback_data="stats:prelands")],
        [InlineKeyboardButton(text="⚠️ Ошибки доставки", callback_data="stats:errors")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main:menu")],
    ])
