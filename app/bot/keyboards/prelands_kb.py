from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def prelands_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить preland", callback_data="prelands:add")],
            [InlineKeyboardButton(text="📋 Список prelands", callback_data="prelands:list")],
            [InlineKeyboardButton(text="📎 Tracking code", callback_data="prelands:tracking_code")],
            [InlineKeyboardButton(text="🧪 Тест события", callback_data="prelands:test")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main:menu")],
        ]
    )


def preland_card_kb(preland_id: int, slug: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📎 Tracking code", callback_data=f"prelands:code:{slug}")],
            [
                InlineKeyboardButton(text="📊 Сегодня", callback_data=f"prelands:stats_today:{preland_id}"),
                InlineKeyboardButton(text="📊 7 дней", callback_data=f"prelands:stats_7:{preland_id}"),
                InlineKeyboardButton(text="📊 30 дней", callback_data=f"prelands:stats_30:{preland_id}"),
            ],
            [
                InlineKeyboardButton(text="🧪 Тест page_view", callback_data=f"prelands:test_view:{preland_id}"),
                InlineKeyboardButton(text="🧪 Тест click", callback_data=f"prelands:test_click:{preland_id}"),
            ],
            [InlineKeyboardButton(text="✏️ Изменить", callback_data=f"prelands:edit:{preland_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="prelands:menu")],
        ]
    )
