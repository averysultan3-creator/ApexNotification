from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать форму", callback_data="funnel:create")],
        [
            InlineKeyboardButton(text="📋 Мои формы", callback_data="funnel:list"),
            InlineKeyboardButton(text="📥 Лиды", callback_data="leads:menu"),
        ],
        [
            InlineKeyboardButton(text="🌐 Prelands", callback_data="prelands:menu"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats:menu"),
        ],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings:menu")],
    ])
