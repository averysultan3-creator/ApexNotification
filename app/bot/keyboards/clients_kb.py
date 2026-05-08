from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def clients_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить клиента", callback_data="clients:add")],
        [InlineKeyboardButton(text="📋 Список", callback_data="clients:list")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main:menu")],
    ])


def client_card_kb(client_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Telegram ID", callback_data=f"clients:add_tid:{client_id}")],
        [InlineKeyboardButton(text="📊 Google Sheet", callback_data=f"clients:set_sheet:{client_id}")],
        [InlineKeyboardButton(text="📥 Лиды клиента", callback_data=f"clients:leads:{client_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="clients:list")],
    ])


def clients_list_kb(clients: list) -> InlineKeyboardMarkup:
    buttons = []
    for client in clients:
        status = "✅" if client.status == "active" else "⏸"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {client.name}", callback_data=f"clients:card:{client.id}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="clients:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
