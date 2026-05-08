from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def forms_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить форму", callback_data="forms:add")],
        [InlineKeyboardButton(text="📋 Список форм", callback_data="forms:list")],
        [InlineKeyboardButton(text="🧪 Тест", callback_data="forms:test")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main:menu")],
    ])


def form_card_kb(form_id: int, is_active: bool = True) -> InlineKeyboardMarkup:
    toggle_label = "⏸ Выкл" if is_active else "▶️ Вкл"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧪 Тест лид", callback_data=f"forms:test_lead:{form_id}")],
        [InlineKeyboardButton(text="📥 Лиды формы", callback_data=f"forms:leads:{form_id}")],
        [InlineKeyboardButton(text=toggle_label, callback_data=f"forms:toggle:{form_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="forms:list")],
    ])


def forms_list_kb(forms: list) -> InlineKeyboardMarkup:
    buttons = []
    for form in forms:
        status = "✅" if form.status == "active" else "⏸"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {form.name}", callback_data=f"forms:card:{form.id}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="forms:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def clients_select_kb(clients: list) -> InlineKeyboardMarkup:
    buttons = []
    for client in clients:
        buttons.append([InlineKeyboardButton(
            text=client.name, callback_data=f"forms:select_client:{client.id}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="forms:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
