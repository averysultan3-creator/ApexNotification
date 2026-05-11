from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def prelands_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Мои сайты", callback_data="pl:sites")],
        [InlineKeyboardButton(text="➕ Добавить сайт", callback_data="pl:site:add")],
        [InlineKeyboardButton(text="📦 Архив прелендов", callback_data="prelands:archive_list")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="main:menu")],
    ])


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------

def sites_list_kb(sites: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"🌐 {s.name}",
            callback_data=f"pl:site:{s.id}",
        )]
        for s in sites
    ]
    buttons.append([InlineKeyboardButton(text="➕ Добавить сайт", callback_data="pl:site:add")])
    buttons.append([InlineKeyboardButton(text="📦 Архив сайтов", callback_data="pl:sites:archived")])
    buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="pl:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def site_card_kb(site_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Ссылки сайта", callback_data=f"pl:links:{site_id}")],
        [InlineKeyboardButton(text="➕ Создать ссылку", callback_data=f"pl:link:add:{site_id}")],
        [InlineKeyboardButton(text="📊 Статистика сайта", callback_data=f"pl:site:stats:{site_id}:7d")],
        [InlineKeyboardButton(text="📄 Код для сайта", callback_data=f"pl:site:code:{site_id}")],
        [InlineKeyboardButton(text="� Проверить трекинг", callback_data=f"pl:site:check:{site_id}")],
        [InlineKeyboardButton(text="�📦 Архивировать", callback_data=f"pl:site:archive:{site_id}")],
        [InlineKeyboardButton(text="⬅ К списку", callback_data="pl:sites")],
    ])


def site_archived_card_kb(site_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♻️ Восстановить", callback_data=f"pl:site:restore:{site_id}")],
        [InlineKeyboardButton(text="⬅ Архив сайтов", callback_data="pl:sites:archived")],
    ])


def site_stats_period_kb(site_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Сегодня", callback_data=f"pl:site:stats:{site_id}:today"),
            InlineKeyboardButton(text="7 дней", callback_data=f"pl:site:stats:{site_id}:7d"),
            InlineKeyboardButton(text="30 дней", callback_data=f"pl:site:stats:{site_id}:30d"),
        ],
        [InlineKeyboardButton(text="⬅ К сайту", callback_data=f"pl:site:{site_id}")],
    ])


# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------

def links_list_kb(links: list, site_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"🔗 {lnk.display_name}",
            callback_data=f"pl:link:{lnk.id}",
        )]
        for lnk in links
    ]
    buttons.append([InlineKeyboardButton(text="➕ Создать ссылку", callback_data=f"pl:link:add:{site_id}")])
    buttons.append([InlineKeyboardButton(text="⬅ К сайту", callback_data=f"pl:site:{site_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def link_card_kb(link_id: int, site_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data=f"pl:link:stats:{link_id}:7d")],
        [InlineKeyboardButton(text="� Проверить трекинг", callback_data=f"pl:link:check:{link_id}")],
        [InlineKeyboardButton(text="📜 Код для сайта", callback_data=f"pl:link:code:{link_id}")],
        [InlineKeyboardButton(text="�📋 Все ссылки сайта", callback_data=f"pl:links:{site_id}")],
        [InlineKeyboardButton(text="📦 Архивировать", callback_data=f"pl:link:archive:{link_id}")],
        [InlineKeyboardButton(text="⬅ К сайту", callback_data=f"pl:site:{site_id}")],
    ])


def link_stats_period_kb(link_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Сегодня", callback_data=f"pl:link:stats:{link_id}:today"),
            InlineKeyboardButton(text="7 дней", callback_data=f"pl:link:stats:{link_id}:7d"),
            InlineKeyboardButton(text="30 дней", callback_data=f"pl:link:stats:{link_id}:30d"),
        ],
        [InlineKeyboardButton(text="⏱ По часам", callback_data=f"pl:link:stats:{link_id}:hourly")],
        [InlineKeyboardButton(text="⬅ К ссылке", callback_data=f"pl:link:{link_id}")],
    ])


def link_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Создать", callback_data="pl:link:do_create")],
        [InlineKeyboardButton(text="✏️ Изменить", callback_data="pl:link:reenter")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="pl:link:cancel")],
    ])


# ---------------------------------------------------------------------------
# Legacy aliases — kept so old preland handlers still compile
# ---------------------------------------------------------------------------

def preland_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Создать", callback_data="prelands:do_create")],
        [InlineKeyboardButton(text="✏️ Изменить название", callback_data="prelands:reenter")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="prelands:cancel")],
    ])


def preland_card_kb(preland_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Код", callback_data=f"prelands:code:{preland_id}")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data=f"prelands:stats:{preland_id}")],
        [InlineKeyboardButton(text="📦 Архивировать", callback_data=f"prelands:archive:{preland_id}")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="prelands:list")],
    ])


def preland_archived_card_kb(preland_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♻️ Восстановить", callback_data=f"prelands:restore:{preland_id}")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="prelands:archive_list")],
    ])


def prelands_archive_list_kb(prelands: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"📦 {p.display_name or p.name}",
            callback_data=f"prelands:archived_card:{p.id}",
        )]
        for p in prelands
    ]
    buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="prelands:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def prelands_list_kb(prelands: list) -> InlineKeyboardMarkup:
    buttons = []
    for preland in prelands:
        status = "🟢" if preland.status == "active" else "🔴"
        label = getattr(preland, "display_name", None) or preland.name
        buttons.append([InlineKeyboardButton(
            text=f"{status} {label}", callback_data=f"prelands:card:{preland.id}",
        )])
    buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="prelands:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

