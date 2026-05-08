from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📥 Лиды", callback_data="leads:menu"),
                InlineKeyboardButton(text="📋 FB Формы", callback_data="fbforms:menu"),
            ],
            [
                InlineKeyboardButton(text="👥 Клиенты", callback_data="clients:menu"),
                InlineKeyboardButton(text="🔀 Правила", callback_data="rules:menu"),
            ],
            [
                InlineKeyboardButton(text="🌐 Prelands", callback_data="prelands:menu"),
                InlineKeyboardButton(text="📊 Статистика", callback_data="stats:menu"),
            ],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings:menu")],
        ]
    )


def back_home_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное", callback_data="main:menu")]])
