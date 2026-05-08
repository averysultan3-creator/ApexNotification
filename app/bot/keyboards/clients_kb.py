from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def clients_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить клиента", callback_data="clients:add")],
            [InlineKeyboardButton(text="📋 Список клиентов", callback_data="clients:list")],
            [InlineKeyboardButton(text="🔍 Найти клиента", callback_data="clients:search")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main:menu")],
        ]
    )


def client_card_kb(client_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Telegram ID", callback_data=f"clients:add_tg:{client_id}"),
                InlineKeyboardButton(text="➕ Email", callback_data=f"clients:add_email:{client_id}"),
            ],
            [InlineKeyboardButton(text="📋 FB формы", callback_data=f"fbforms:client:{client_id}")],
            [InlineKeyboardButton(text="📥 Лиды клиента", callback_data=f"leads:client:{client_id}")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data=f"clients:stats:{client_id}")],
            [InlineKeyboardButton(text="🧪 Тест отправки", callback_data=f"clients:test:{client_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="clients:menu")],
        ]
    )
