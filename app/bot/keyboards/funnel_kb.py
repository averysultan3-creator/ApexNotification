from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def funnel_list_kb(forms: list, show_archive_button: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    for form in forms:
        icon = "\U0001f7e2" if form.status == "active" else "\U0001f534"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {form.form_name}",
            callback_data=f"funnel:card:{form.id}",
        )])
    buttons.append([InlineKeyboardButton(text="\u2795 Новая воронка", callback_data="funnel:create")])
    if show_archive_button:
        buttons.append([InlineKeyboardButton(text="\U0001f4e6 Архив", callback_data="funnel:archive_list")])
    buttons.append([InlineKeyboardButton(text="\u2b05 Назад", callback_data="main:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def funnel_archive_list_kb(forms: list) -> InlineKeyboardMarkup:
    buttons = []
    for form in forms:
        buttons.append([InlineKeyboardButton(
            text=f"\U0001f4e6 {form.form_name}",
            callback_data=f"funnel:archived_card:{form.id}",
        )])
    buttons.append([InlineKeyboardButton(text="\u2b05 Назад", callback_data="funnel:list")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def funnel_archived_card_kb(form_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u267b\ufe0f Восстановить", callback_data=f"funnel:restore:{form_id}")],
        [InlineKeyboardButton(text="\u2b05 Назад", callback_data="funnel:archive_list")],
    ])


def funnel_card_kb(form_id: int, is_active: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f4dc Код для Google Sheet", callback_data=f"funnel:code:{form_id}")],
        [InlineKeyboardButton(text="\U0001f517 Ссылка для клиента", callback_data=f"funnel:joinlink:{form_id}")],
        [
            InlineKeyboardButton(text="\U0001f4cb Лиды", callback_data=f"funnel:leads:{form_id}"),
            InlineKeyboardButton(text="\U0001f4ca Статистика", callback_data=f"funnel:stats:{form_id}"),
        ],
        [InlineKeyboardButton(text="👥 Получатели", callback_data=f"funnel:recipients:{form_id}")],
        [
            InlineKeyboardButton(text="\u270f\ufe0f Переименовать / Тег", callback_data=f"funnel:rename:{form_id}"),
        ],
        [InlineKeyboardButton(text="🔌 Проверить соединение", callback_data=f"funnel:checkconnection:{form_id}")],
        [
            InlineKeyboardButton(text="\U0001f4e6 Архивировать", callback_data=f"funnel:archive:{form_id}"),
        ],
        [InlineKeyboardButton(text="\u2b05 Назад", callback_data="funnel:list")],
    ])


def funnel_delete_confirm_kb(form_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"funnel:delete_confirm:{form_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"funnel:card:{form_id}")],
    ])


def funnel_created_kb(form_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f4dc Код для Google Sheet", callback_data=f"funnel:code:{form_id}")],
        [InlineKeyboardButton(text="\U0001f517 Ссылка для клиента", callback_data=f"funnel:joinlink:{form_id}")],
        [InlineKeyboardButton(text="\U0001f9ea Тест", callback_data=f"funnel:test:{form_id}")],
        [InlineKeyboardButton(text="\U0001f4ca Статистика", callback_data=f"funnel:stats:{form_id}")],
        [InlineKeyboardButton(text="\U0001f3e0 Главное меню", callback_data="main:menu")],
    ])


def funnel_join_notify_kb(form_id: int, recipient_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="\U0001f4e6 Отправить архив лидов",
                callback_data=f"funnel:sendold_exec:{recipient_id}:{form_id}",
            ),
        ],
        [InlineKeyboardButton(text="\U0001f4cb Лиды воронки", callback_data=f"funnel:leads:{form_id}")],
    ])


def funnel_sendold_menu_kb(recipients: list, form_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text="All recipients",
            callback_data=f"funnel:sendold_all:{form_id}",
        )],
    ]
    for recipient in recipients:
        name = recipient.first_name or recipient.telegram_username or str(recipient.telegram_user_id)
        buttons.append([InlineKeyboardButton(
            text=name,
            callback_data=f"funnel:sendold_exec:{recipient.id}:{form_id}",
        )])
    buttons.append([InlineKeyboardButton(text="Back", callback_data=f"funnel:card:{form_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def funnel_stats_kb(form_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Лиды", callback_data=f"funnel:leads:{form_id}"),
            InlineKeyboardButton(text="👥 Получатели", callback_data=f"funnel:recipients:{form_id}"),
        ],
        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"funnel:card:{form_id}")],
    ])


def recipients_list_kb(recipients: list, form_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for recipient in recipients:
        name = recipient.first_name or recipient.telegram_username or str(recipient.telegram_user_id)
        status = "✅" if recipient.status == "active" else "⏸"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status} {name}",
                callback_data=f"funnel:sendold_exec:{recipient.id}:{form_id}",
            ),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"funnel:delrecip:{recipient.id}:{form_id}"),
        ])
    buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data=f"funnel:card:{form_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def sheet_name_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Sheet1", callback_data="wizard:sheetname:Sheet1")],
        [InlineKeyboardButton(text="Leads", callback_data="wizard:sheetname:Leads")],
        [InlineKeyboardButton(text="Лист1", callback_data="wizard:sheetname:\u041bист1")],
        [InlineKeyboardButton(text="\u23ed Пропустить (Sheet1)", callback_data="wizard:sheetname:Sheet1")],
        [InlineKeyboardButton(text="\u274c Отмена", callback_data="wizard:cancel")],
    ])


def skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\u23ed Пропустить", callback_data="wizard:skip")],
        [InlineKeyboardButton(text="\u274c Отмена", callback_data="wizard:cancel")],
    ])
