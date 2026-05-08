from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def delivery_rules_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать правило", callback_data="rules:add")],
            [InlineKeyboardButton(text="📋 Список правил", callback_data="rules:list")],
            [InlineKeyboardButton(text="⚠️ Ошибки доставки", callback_data="leads:errors")],
            [InlineKeyboardButton(text="🧪 Тест правила", callback_data="rules:test")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main:menu")],
        ]
    )


def rule_card_kb(rule_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить получателей", callback_data=f"rules:edit:{rule_id}")],
            [
                InlineKeyboardButton(text="✅/❌ Admin", callback_data=f"rules:toggle_admin:{rule_id}"),
                InlineKeyboardButton(text="✅/❌ Telegram", callback_data=f"rules:edit_tg:{rule_id}"),
            ],
            [
                InlineKeyboardButton(text="✅/❌ Email", callback_data=f"rules:edit_email:{rule_id}"),
                InlineKeyboardButton(text="✅/❌ Google Sheet", callback_data=f"rules:edit_sheet:{rule_id}"),
            ],
            [InlineKeyboardButton(text="🧪 Тест", callback_data=f"rules:test:{rule_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="rules:menu")],
        ]
    )
