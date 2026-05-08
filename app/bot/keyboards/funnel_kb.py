from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def funnel_list_kb(forms: list) -> InlineKeyboardMarkup:
    buttons = []
    for f in forms:
        icon = "🟢" if f.status == "active" else "🔴"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {f.form_name}",
            callback_data=f"funnel:card:{f.id}",
        )])
    buttons.append([InlineKeyboardButton(text="➕ Создать форму", callback_data="funnel:create")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def funnel_card_kb(form_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_text = "⏸ Выключить" if is_active else "▶️ Включить"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Код Apps Script", callback_data=f"funnel:code:{form_id}")],
        [InlineKeyboardButton(text="👥 Подключить клиента", callback_data=f"funnel:joinlink:{form_id}")],
        [
            InlineKeyboardButton(text="📥 Лиды формы", callback_data=f"funnel:leads:{form_id}"),
            InlineKeyboardButton(text="👤 Получатели", callback_data=f"funnel:recipients:{form_id}"),
        ],
        [InlineKeyboardButton(text=toggle_text, callback_data=f"funnel:toggle:{form_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="funnel:list")],
    ])


def funnel_join_notify_kb(form_id: int, recipient_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📤 Все старые", callback_data=f"funnel:sendold:{recipient_id}:all"),
            InlineKeyboardButton(text="📤 Последние 20", callback_data=f"funnel:sendold:{recipient_id}:last20"),
        ],
        [InlineKeyboardButton(text="⏭ Только новые", callback_data=f"funnel:sendold:{recipient_id}:skip")],
        [InlineKeyboardButton(text="📥 Лиды формы", callback_data=f"funnel:leads:{form_id}")],
    ])


def funnel_sendold_options_kb(recipient_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📤 Все", callback_data=f"funnel:sendold:{recipient_id}:all"),
            InlineKeyboardButton(text="📤 Последние 20", callback_data=f"funnel:sendold:{recipient_id}:last20"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="funnel:list")],
    ])


def recipients_list_kb(recipients: list, form_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for r in recipients:
        name = r.first_name or r.telegram_username or str(r.telegram_user_id)
        buttons.append([
            InlineKeyboardButton(text=f"👤 {name}", callback_data=f"funnel:sendold:{r.id}:choose"),
            InlineKeyboardButton(text="❌", callback_data=f"funnel:delrecip:{r.id}:{form_id}"),
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"funnel:card:{form_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def sheet_choice_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, подключить таблицу", callback_data="wizard:sheet:yes")],
        [InlineKeyboardButton(text="⏭ Позже", callback_data="wizard:sheet:skip")],
    ])


def skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="wizard:skip")],
    ])
