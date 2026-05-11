from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Лиды", callback_data="leads:menu"),
            InlineKeyboardButton(text="📁 Воронки", callback_data="funnel:list"),
        ],
        [
            InlineKeyboardButton(text="➕ Новая воронка", callback_data="funnel:create"),
            InlineKeyboardButton(text="🌐 Преленды", callback_data="pl:menu"),
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats:menu"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings:menu"),
        ],
    ])
