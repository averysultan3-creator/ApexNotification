from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def stats_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📥 Лиды сегодня", callback_data="stats:leads_today")],
            [InlineKeyboardButton(text="📋 По FB формам", callback_data="stats:forms")],
            [InlineKeyboardButton(text="👥 По клиентам", callback_data="stats:clients")],
            [InlineKeyboardButton(text="🌐 Prelands", callback_data="stats:prelands")],
            [InlineKeyboardButton(text="⚠️ Ошибки доставки", callback_data="stats:errors")],
            [InlineKeyboardButton(text="📤 Экспорт", callback_data="leads:export")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main:menu")],
        ]
    )


def settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Webhook данные", callback_data="settings:webhook")],
            [InlineKeyboardButton(text="📎 Tracking script", callback_data="settings:tracking")],
            [InlineKeyboardButton(text="🧪 Health check", callback_data="settings:health")],
            [InlineKeyboardButton(text="📖 Инструкция подключения", callback_data="settings:guide")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main:menu")],
        ]
    )
