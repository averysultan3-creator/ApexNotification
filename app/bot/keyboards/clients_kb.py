from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def clients_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить клиента", callback_data="clients:add")],
        [InlineKeyboardButton(text="📋 Список", callback_data="clients:list")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main:menu")],
    ])


def client_card_kb(client_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Реф-ссылка для получателя", callback_data=f"clients:reflink:{client_id}")],
        [InlineKeyboardButton(text="📊 Google Sheet", callback_data=f"clients:set_sheet:{client_id}")],
        [InlineKeyboardButton(text="📥 Лиды клиента", callback_data=f"clients:leads:{client_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="clients:list")],
    ])


def client_reflink_kb(client_id: int, tg_ids: list) -> InlineKeyboardMarkup:
    buttons = []
    for tid in tg_ids:
        buttons.append([InlineKeyboardButton(
            text=f"❌ Удалить {tid}", callback_data=f"clients:del_tid:{client_id}:{tid}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"clients:card:{client_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def clients_list_kb(clients: list) -> InlineKeyboardMarkup:
    buttons = []
    for client in clients:
        status = "✅" if client.status == "active" else "⏸"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {client.name}", callback_data=f"clients:card:{client.id}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="clients:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
