from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def prelands_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить", callback_data="prelands:add")],
        [InlineKeyboardButton(text="📋 Список", callback_data="prelands:list")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main:menu")],
    ])


def preland_card_kb(preland_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Код", callback_data=f"prelands:code:{preland_id}")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data=f"prelands:stats:{preland_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="prelands:list")],
    ])


def prelands_list_kb(prelands: list) -> InlineKeyboardMarkup:
    buttons = []
    for p in prelands:
        status = "✅" if p.status == "active" else "⏸"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {p.name}", callback_data=f"prelands:card:{p.id}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="prelands:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
