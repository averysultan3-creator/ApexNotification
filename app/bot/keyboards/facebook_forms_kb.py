from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def facebook_forms_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить FB форму", callback_data="fbforms:add")],
            [InlineKeyboardButton(text="📋 Список форм", callback_data="fbforms:list")],
            [InlineKeyboardButton(text="🔗 Webhook инструкция", callback_data="fbforms:webhook")],
            [InlineKeyboardButton(text="🧪 Тестовый лид", callback_data="fbforms:test")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main:menu")],
        ]
    )


def facebook_form_card_kb(form_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔀 Куда отправлять", callback_data=f"rules:create_for_form:{form_id}")],
            [InlineKeyboardButton(text="🧪 Тестовый лид", callback_data=f"fbforms:test:{form_id}")],
            [InlineKeyboardButton(text="📥 Лиды формы", callback_data=f"leads:form:{form_id}")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data=f"fbforms:stats:{form_id}")],
            [
                InlineKeyboardButton(text="✏️ Изменить", callback_data=f"fbforms:edit:{form_id}"),
                InlineKeyboardButton(text="⏸ Выключить", callback_data=f"fbforms:toggle:{form_id}"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="fbforms:menu")],
        ]
    )
