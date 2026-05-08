from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📥 Лиды", callback_data="leads:menu"),
            InlineKeyboardButton(text="📋 FB формы", callback_data="forms:menu"),
        ],
        [
            InlineKeyboardButton(text="👥 Клиенты", callback_data="clients:menu"),
            InlineKeyboardButton(text="🌐 Prelands", callback_data="prelands:menu"),
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats:menu"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings:menu"),
        ],
    ])
