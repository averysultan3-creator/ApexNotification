from datetime import datetime, timedelta
from html import escape

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.prelands_kb import (
    link_card_kb,
    link_confirm_kb,
    link_stats_period_kb,
    links_list_kb,
    preland_archived_card_kb,
    preland_card_kb,
    preland_confirm_kb,
    prelands_archive_list_kb,
    prelands_list_kb,
    prelands_menu_kb,
    site_archived_card_kb,
    site_card_kb,
    site_stats_period_kb,
    sites_list_kb,
)
from app.bot.keyboards.main_kb import main_menu_kb
from app.bot.states.preland_states import AddLinkFSM, AddPrelandFSM, AddSiteFSM
from app.services.preland_link_service import (
    archive_link,
    generate_unique_slug,
    get_link_by_id,
    list_links_for_site,
)
from app.services.preland_name_service import parse_preland_input
from app.services.preland_service import (
    archive_preland,
    create_preland,
    get_preland_by_id,
    list_archived_prelands,
    list_prelands,
    restore_preland,
)
from app.services.preland_site_service import (
    archive_site,
    create_site,
    get_site_by_id,
    list_archived_sites,
    list_sites,
    restore_site,
)
from app.services.preland_tracking_service import (
    generate_tracking_script,
    get_link_button_stats,
    get_link_hourly_stats,
    get_link_recent_events,
    get_link_stats,
    get_preland_button_stats,
    get_preland_stats,
    get_site_recent_events,
    get_site_stats,
    check_site_event_since,
)
from config import PUBLIC_BASE_URL

router = Router(name="prelands")


@router.callback_query(lambda c: c.data == "prelands:menu")
async def prelands_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    prelands = await list_prelands(session, active_only=True)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total_views = total_clicks = 0
    for preland in prelands:
        stats = await get_preland_stats(session, preland.id, date_from=today_start)
        total_views += stats["visits"]
        total_clicks += stats["clicks"]
    ctr = round(total_clicks / total_views * 100, 1) if total_views else 0.0
    text = (
        "<b>\U0001f310 Преленды</b>\n\n"
        "Сегодня:\n"
        f"Просмотры: {total_views}\n"
        f"Клики: {total_clicks}\n"
        f"CTR: {ctr}%"
    )
    await callback.message.edit_text(text, reply_markup=prelands_menu_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "prelands:add")
async def prelands_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddPrelandFSM.name)
    await callback.message.edit_text(
        "<b>🌐 Новый преленд</b>\n\n"
        "Введите название в свободной форме:\n"
        "<i>убер польша сторис девушки</i>\n"
        "<i>uberland pl reels men driver</i>\n"
        "<i>skyx cz feed broad</i>\n\n"
        "Бот сам сгенерирует slug и ссылку.\n"
        "/cancel — отмена"
    )
    await callback.answer()


@router.message(lambda m: m.text and m.text.strip() == "/cancel", AddPrelandFSM.name)
@router.message(lambda m: m.text and m.text.strip() == "/cancel", AddPrelandFSM.confirm)
@router.message(lambda m: m.text and m.text.strip() == "/cancel", AddPrelandFSM.slug)
@router.message(lambda m: m.text and m.text.strip() == "/cancel", AddPrelandFSM.url)
async def prelands_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_kb())


@router.message(AddPrelandFSM.name)
async def prelands_add_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.text or not message.text.strip():
        await message.answer("Отправьте название текстом.")
        return
    raw = message.text.strip()
    parsed = parse_preland_input(raw)
    slug = await generate_unique_slug(session, parsed.slug_base)
    script_tag = f'<script src="{PUBLIC_BASE_URL}/track/pixel.js?pl={slug}"></script>'
    ad_url_hint = f"yoursite.com/preland/?pl={slug}"
    await state.update_data(raw=raw, display_name=parsed.display_name, slug=slug)
    await state.set_state(AddPrelandFSM.confirm)
    await message.answer(
        f"<b>📋 Предпросмотр</b>\n\n"
        f"<b>Название:</b> {escape(parsed.display_name)}\n"
        f"<b>Slug:</b> <code>{escape(slug)}</code>\n\n"
        f"<b>Скрипт трекинга</b> (вставить перед &lt;/body&gt;):\n"
        f"<pre>{escape(script_tag)}</pre>\n"
        f"<b>Ссылка в рекламе:</b> <code>{escape(ad_url_hint)}</code>\n\n"
        "Всё верно?",
        reply_markup=preland_confirm_kb(),
    )


@router.callback_query(lambda c: c.data == "prelands:do_create", AddPrelandFSM.confirm)
async def prelands_do_create(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    display_name = data.get("display_name", "")
    slug = data.get("slug", "")
    raw = data.get("raw", display_name)
    try:
        preland = await create_preland(
            session, name=raw, slug=slug, url=None, display_name=display_name
        )
        await state.clear()
        script = f'<script src="{PUBLIC_BASE_URL}/track/pixel.js?pl={preland.slug}"></script>'
        await callback.message.edit_text(
            f"<b>✅ Создан: {escape(display_name)}</b>\n\n"
            f"Slug: <code>{escape(preland.slug)}</code>\n\n"
            f"Скрипт (вставить перед &lt;/body&gt;):\n<pre>{escape(script)}</pre>",
            reply_markup=preland_card_kb(preland.id),
        )
    except Exception as exc:
        await state.clear()
        await callback.message.edit_text(f"Ошибка: {escape(str(exc))}", reply_markup=prelands_menu_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "prelands:reenter", AddPrelandFSM.confirm)
async def prelands_reenter(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddPrelandFSM.name)
    await callback.message.edit_text(
        "<b>✏️ Введите название заново</b>\n\n"
        "Пример: <code>uber pl story girls fastjob</code>\n/cancel — отмена"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "prelands:cancel", AddPrelandFSM.confirm)
async def prelands_confirm_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Отменено.", reply_markup=prelands_menu_kb())
    await callback.answer()


@router.message(AddPrelandFSM.slug)
async def prelands_add_slug(message: Message, state: FSMContext) -> None:
    await message.answer("Этот шаг больше не нужен — slug генерируется автоматически. Создайте преленд заново.")
    await state.clear()


@router.callback_query(lambda c: c.data == "prelands:list")
async def prelands_list(callback: CallbackQuery, session: AsyncSession) -> None:
    prelands = await list_prelands(session)
    if not prelands:
        await callback.answer("Прелендов пока нет.", show_alert=True)
        return
    await callback.message.edit_text("Преленды:", reply_markup=prelands_list_kb(prelands))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("prelands:card:"))
async def preland_card(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    preland_id = int(callback.data.split(":")[2])
    preland = await get_preland_by_id(session, preland_id)
    if not preland:
        await callback.answer("Преленд не найден.", show_alert=True)
        return
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = datetime.utcnow() - timedelta(days=7)
    stats_today = await get_preland_stats(session, preland.id, date_from=today_start)
    stats_7d = await get_preland_stats(session, preland.id, date_from=week_start)
    button_stats = await get_preland_button_stats(session, preland.id)
    button_text = "\n".join(f"  {escape(key)}: {value}" for key, value in button_stats.items()) if button_stats else "  -"
    display = preland.display_name or preland.name
    text = (
        f"<b>{escape(display)}</b>\n"
        f"<code>{escape(preland.slug)}</code>\n\n"
        f"Сегодня: 👁 {stats_today['visits']} 👆 {stats_today['clicks']} CTR {stats_today['ctr']}%\n"
        f"7 дней: 👁 {stats_7d['visits']} 👆 {stats_7d['clicks']} CTR {stats_7d['ctr']}%\n\n"
        f"Кнопки сегодня:\n{button_text}"
    )
    await callback.message.edit_text(text, reply_markup=preland_card_kb(preland.id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("prelands:code:"))
async def preland_code(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    preland_id = int(callback.data.split(":")[2])
    preland = await get_preland_by_id(session, preland_id)
    if not preland:
        await callback.answer("Преленд не найден.", show_alert=True)
        return
    script = f'<script src="{PUBLIC_BASE_URL}/track/pixel.js?pl={preland.slug}"></script>'
    button_example = '<a href="https://t.me/..." data-track-click="main_cta">Оставить заявку</a>'
    text = (
        f"<b>Код для {escape(preland.name)}</b>\n\n"
        f"Вставьте перед &lt;/body&gt;:\n<pre>{escape(script)}</pre>\n\n"
        f"Для трекинга кликов на кнопках добавьте <code>data-track-click=&quot;имя&quot;</code>:\n<pre>{escape(button_example)}</pre>"
    )
    await callback.message.edit_text(text, reply_markup=preland_card_kb(preland.id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("prelands:stats:"))
async def preland_stats_7d(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    preland_id = int(callback.data.split(":")[2])
    preland = await get_preland_by_id(session, preland_id)
    if not preland:
        await callback.answer("Преленд не найден.", show_alert=True)
        return
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = datetime.utcnow() - timedelta(days=7)
    today = await get_preland_stats(session, preland.id, date_from=today_start)
    week = await get_preland_stats(session, preland.id, date_from=week_start)
    text = (
        f"<b>{escape(preland.display_name or preland.name)}</b>\n"
        f"<code>{escape(preland.slug)}</code>\n\n"
        f"Сегодня: 👁 {today['visits']}  👆 {today['clicks']}  CTR {today['ctr']}%\n"
        f"7 дней: 👁 {week['visits']}  👆 {week['clicks']}  CTR {week['ctr']}%"
    )
    await callback.message.edit_text(text, reply_markup=preland_card_kb(preland.id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("prelands:archive:"))
async def preland_archive(callback: CallbackQuery, session: AsyncSession) -> None:
    preland_id = int(callback.data.split(":")[2])
    preland = await get_preland_by_id(session, preland_id)
    if not preland:
        await callback.answer("Преленд не найден.", show_alert=True)
        return
    await archive_preland(session, preland)
    prelands = await list_prelands(session)
    if prelands:
        await callback.message.edit_text(
            f"<b>📦 Преленд архивирован: {escape(preland.name)}</b>\n\nВосстановить можно в \"📦 Архив\".",
            reply_markup=prelands_list_kb(prelands),
        )
    else:
        await callback.message.edit_text(
            f"<b>📦 Преленд архивирован: {escape(preland.name)}</b>\n\nАктивных прелендов нет.",
            reply_markup=prelands_menu_kb(),
        )
    await callback.answer("Архивировано.")


@router.callback_query(lambda c: c.data == "prelands:archive_list")
async def prelands_archive_list(callback: CallbackQuery, session: AsyncSession) -> None:
    prelands = await list_archived_prelands(session)
    if not prelands:
        await callback.answer("Архив пуст.", show_alert=True)
        return
    await callback.message.edit_text(
        f"<b>📦 Архив прелендов</b>\n\nВсего: {len(prelands)}",
        reply_markup=prelands_archive_list_kb(prelands),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("prelands:archived_card:"))
async def preland_archived_card(callback: CallbackQuery, session: AsyncSession) -> None:
    preland_id = int(callback.data.split(":")[2])
    preland = await get_preland_by_id(session, preland_id)
    if not preland:
        await callback.answer("Преленд не найден.", show_alert=True)
        return
    display = preland.display_name or preland.name
    text = (
        f"<b>📦 {escape(display)}</b>\n"
        f"<code>{escape(preland.slug)}</code>\n"
        f"Статус: Архив\n"
        f"Создан: {preland.created_at:%Y-%m-%d}"
    )
    try:
        await callback.message.edit_text(text, reply_markup=preland_archived_card_kb(preland.id))
    except Exception:
        await callback.message.answer(text, reply_markup=preland_archived_card_kb(preland.id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("prelands:restore:"))
async def preland_restore(callback: CallbackQuery, session: AsyncSession) -> None:
    preland_id = int(callback.data.split(":")[2])
    preland = await get_preland_by_id(session, preland_id)
    if not preland:
        await callback.answer("Преленд не найден.", show_alert=True)
        return
    await restore_preland(session, preland)
    archived = await list_archived_prelands(session)
    if archived:
        await callback.message.edit_text(
            f"<b>♻️ Восстановлен: {escape(preland.name)}</b>\n\nВ архиве осталось: {len(archived)}",
            reply_markup=prelands_archive_list_kb(archived),
        )
    else:
        await callback.message.edit_text(
            f"<b>♻️ Восстановлен: {escape(preland.name)}</b>\n\nАрхив пуст.",
            reply_markup=prelands_menu_kb(),
        )
    await callback.answer("Восстановлено.")


# ===========================================================================
# НОВЫЙ РАЗДЕЛ: PrelandSite + PrelandLink
# ===========================================================================

# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data == "pl:menu")
async def pl_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    sites = await list_sites(session)
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    views = clicks = 0
    for site in sites:
        s = await get_site_stats(session, site.id, date_from=today)
        views += s["visits"]
        clicks += s["clicks"]
    ctr = round(clicks / views * 100, 1) if views else 0.0
    text = (
        "<b>🌐 Трекинг прелендов</b>\n\n"
        f"Сайтов: {len(sites)}\n"
        f"Сегодня: 👁 {views} | 👆 {clicks} | CTR {ctr}%"
    )
    await callback.message.edit_text(text, reply_markup=prelands_menu_kb())
    await callback.answer()


# ---------------------------------------------------------------------------
# Sites list
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data == "pl:sites")
async def pl_sites_list(callback: CallbackQuery, session: AsyncSession) -> None:
    sites = await list_sites(session)
    if not sites:
        await callback.message.edit_text(
            "<b>🌐 Сайтов пока нет</b>\n\nДобавьте первый сайт.",
            reply_markup=sites_list_kb([]),
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        f"<b>🌐 Сайты ({len(sites)})</b>",
        reply_markup=sites_list_kb(sites),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "pl:sites:archived")
async def pl_sites_archived(callback: CallbackQuery, session: AsyncSession) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    archived = await list_archived_sites(session)
    if not archived:
        await callback.answer("Архив сайтов пуст.", show_alert=True)
        return
    buttons = [
        [InlineKeyboardButton(
            text=f"📦 {s.name}",
            callback_data=f"pl:site:archived:{s.id}",
        )]
        for s in archived
    ]
    buttons.append([InlineKeyboardButton(text="⬅ К списку", callback_data="pl:sites")])
    await callback.message.edit_text(
        f"<b>📦 Архив сайтов ({len(archived)})</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("pl:site:archived:"))
async def pl_site_archived_card(callback: CallbackQuery, session: AsyncSession) -> None:
    site_id = int(callback.data.split(":")[3])
    site = await get_site_by_id(session, site_id)
    if not site:
        await callback.answer("Сайт не найден.", show_alert=True)
        return
    text = (
        f"<b>📦 {escape(site.name)}</b>\n"
        f"<code>{escape(site.base_url)}</code>\n"
        f"Статус: Архив\n"
        f"Создан: {site.created_at:%Y-%m-%d}"
    )
    await callback.message.edit_text(text, reply_markup=site_archived_card_kb(site_id))
    await callback.answer()



@router.callback_query(lambda c: c.data == "pl:site:add")
async def pl_site_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddSiteFSM.name)
    await callback.message.edit_text(
        "<b>➕ Новый сайт</b>\n\n"
        "Введите название сайта:\n<i>Ubereats PL</i>\n\n/cancel — отмена"
    )
    await callback.answer()


@router.message(lambda m: m.text and m.text.strip() == "/cancel", AddSiteFSM.name)
@router.message(lambda m: m.text and m.text.strip() == "/cancel", AddSiteFSM.base_url)
async def pl_site_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_kb())


@router.message(AddSiteFSM.name)
async def pl_site_add_name(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip():
        await message.answer("Введите название текстом.")
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(AddSiteFSM.base_url)
    await message.answer(
        "<b>Введите базовый URL сайта</b>\n\n"
        "Например: <code>https://mysite.github.io/preland</code>\n\n"
        "/cancel — отмена"
    )


@router.message(AddSiteFSM.base_url)
async def pl_site_add_url(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.text or not message.text.strip():
        await message.answer("Введите URL текстом.")
        return
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer("URL должен начинаться с http:// или https://")
        return
    data = await state.get_data()
    try:
        site = await create_site(session, name=data["name"], base_url=url)
        await state.clear()
        await message.answer(
            f"<b>✅ Сайт добавлен!</b>\n\n"
            f"<b>Название:</b> {escape(site.name)}\n"
            f"<b>URL:</b> {escape(site.base_url)}\n\n"
            "Теперь создайте первую трекинговую ссылку.",
            reply_markup=site_card_kb(site.id),
        )
    except Exception as exc:
        await state.clear()
        await message.answer(f"Ошибка: {escape(str(exc))}")


# ---------------------------------------------------------------------------
# Site card
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data and c.data.startswith("pl:site:") and c.data[8:].isdigit())
async def pl_site_card(callback: CallbackQuery, session: AsyncSession) -> None:
    site_id = int(callback.data.split(":")[2])
    site = await get_site_by_id(session, site_id)
    if not site:
        await callback.answer("Сайт не найден.", show_alert=True)
        return
    links = await list_links_for_site(session, site_id)
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    s = await get_site_stats(session, site_id, date_from=today)
    text = (
        f"<b>🌐 {escape(site.name)}</b>\n"
        f"<code>{escape(site.base_url)}</code>\n\n"
        f"Ссылок: {len(links)}\n"
        f"Сегодня: 👁 {s['visits']} | 👆 {s['clicks']} | CTR {s['ctr']}%"
    )
    await callback.message.edit_text(text, reply_markup=site_card_kb(site_id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("pl:site:code:"))
async def pl_site_code(callback: CallbackQuery, session: AsyncSession) -> None:
    site_id = int(callback.data.split(":")[3])
    site = await get_site_by_id(session, site_id)
    if not site:
        await callback.answer("Сайт не найден.", show_alert=True)
        return
    # Site-level script: reads ?pl= from ad URL automatically
    js_code = generate_tracking_script(slug=None)
    inline_tag = f"<script>\n{js_code}\n</script>"
    text = (
        f"<b>📄 Код для сайта: {escape(site.name)}</b>\n\n"
        "Вставьте <b>один раз</b> перед &lt;/body&gt;:\n"
        f"<pre>{escape(inline_tag)}</pre>\n\n"
        "Скрипт сам читает <code>?pl=slug</code> из URL рекламной ссылки.\n"
        "Кнопки Telegram/WhatsApp трекаются автоматически.\n"
        "Для кастомных кнопок:\n"
        '<pre>&lt;a href="..." data-track-click="cta"&gt;Кнопка&lt;/a&gt;</pre>'
    )
    await callback.message.edit_text(text, reply_markup=site_card_kb(site_id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("pl:site:check:"))
async def pl_site_check(callback: CallbackQuery, session: AsyncSession) -> None:
    import time
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    parts = callback.data.split(":")
    site_id = int(parts[3])

    # Step 2: pl:site:check:{site_id}:{since_ts} — verify result
    if len(parts) == 5:
        since_ts = float(parts[4])
        site = await get_site_by_id(session, site_id)
        site_name = escape(site.name) if site else str(site_id)
        ok = await check_site_event_since(
            session, site_id, site.base_url if site else "", since_ts
        )
        if ok:
            text = (
                f"<b>✅ Трекинг работает! {site_name}</b>\n\n"
                "Событие от скрипта получено.\n"
                "Скрипт на сайте подключён и отправляет данные на сервер."
            )
        else:
            text = (
                f"<b>❌ Событие не получено: {site_name}</b>\n\n"
                "Убедитесь что:\n"
                "1. Скрипт вставлен перед &lt;/body&gt; и запушен на GitHub\n"
                "2. Открыли именно сайт после нажатия «Новый тест» (не старую вкладку)\n"
                f"3. Сервер доступен: <code>{PUBLIC_BASE_URL}/health</code>\n\n"
                "Попробуйте ещё раз:"
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Новый тест", callback_data=f"pl:site:check:{site_id}")],
            [InlineKeyboardButton(text="⬅ К сайту", callback_data=f"pl:site:{site_id}")],
        ])
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer()
        return

    # Step 1: record start time and show instructions
    site = await get_site_by_id(session, site_id)
    if not site:
        await callback.answer("Сайт не найден.", show_alert=True)
        return
    since_ts = int(time.time())
    site_url = site.base_url.rstrip("/") if site.base_url else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Я открыл — проверить",
            callback_data=f"pl:site:check:{site_id}:{since_ts}",
        )],
        [InlineKeyboardButton(text="⬅ К сайту", callback_data=f"pl:site:{site_id}")],
    ])
    text = (
        f"<b>🔍 Проверка трекинга: {escape(site.name)}</b>\n\n"
        "1. Открой сайт в браузере:\n"
        f"<code>{site_url}</code>\n\n"
        "2. Подожди 3–5 секунд и нажми кнопку ниже."
    )
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("pl:site:stats:"))
async def pl_site_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    parts = callback.data.split(":")
    site_id = int(parts[3])
    period = parts[4] if len(parts) > 4 else "7d"
    site = await get_site_by_id(session, site_id)
    if not site:
        await callback.answer("Сайт не найден.", show_alert=True)
        return
    now = datetime.utcnow()
    if period == "today":
        date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_label = "Сегодня"
    elif period == "30d":
        date_from = now - timedelta(days=30)
        period_label = "30 дней"
    else:
        date_from = now - timedelta(days=7)
        period_label = "7 дней"
    s = await get_site_stats(session, site_id, date_from=date_from)
    links = await list_links_for_site(session, site_id)
    rows = []
    for lnk in links:
        ls = await get_link_stats(session, lnk.id, date_from=date_from)
        if ls["visits"] > 0:
            rows.append(f"  {escape(lnk.display_name)}: 👁{ls['visits']} 👆{ls['clicks']} {ls['ctr']}%")
    top_text = ("\n".join(rows) or "  нет данных")
    text = (
        f"<b>📊 {escape(site.name)} — {period_label}</b>\n\n"
        f"👁 Просмотры: {s['visits']}\n"
        f"👆 Клики: {s['clicks']}\n"
        f"CTR: {s['ctr']}%\n\n"
        f"<b>По ссылкам:</b>\n{top_text}"
    )
    await callback.message.edit_text(text, reply_markup=site_stats_period_kb(site_id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("pl:site:archive:"))
async def pl_site_archive(callback: CallbackQuery, session: AsyncSession) -> None:
    site_id = int(callback.data.split(":")[3])
    site = await get_site_by_id(session, site_id)
    if not site:
        await callback.answer("Сайт не найден.", show_alert=True)
        return
    await archive_site(session, site)
    sites = await list_sites(session)
    await callback.message.edit_text(
        f"<b>📦 Архивировано: {escape(site.name)}</b>",
        reply_markup=sites_list_kb(sites),
    )
    await callback.answer("Архивировано.")


@router.callback_query(lambda c: c.data and c.data.startswith("pl:site:restore:"))
async def pl_site_restore(callback: CallbackQuery, session: AsyncSession) -> None:
    site_id = int(callback.data.split(":")[3])
    site = await get_site_by_id(session, site_id)
    if not site:
        await callback.answer("Сайт не найден.", show_alert=True)
        return
    await restore_site(session, site)
    sites = await list_sites(session)
    await callback.message.edit_text(
        f"<b>♻️ Восстановлено: {escape(site.name)}</b>",
        reply_markup=sites_list_kb(sites),
    )
    await callback.answer("Восстановлено.")


# ---------------------------------------------------------------------------
# Links list
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data and c.data.startswith("pl:links:"))
async def pl_links_list(callback: CallbackQuery, session: AsyncSession) -> None:
    site_id = int(callback.data.split(":")[2])
    site = await get_site_by_id(session, site_id)
    if not site:
        await callback.answer("Сайт не найден.", show_alert=True)
        return
    links = await list_links_for_site(session, site_id)
    text = f"<b>🔗 Ссылки: {escape(site.name)}</b>\n\nВсего: {len(links)}"
    await callback.message.edit_text(text, reply_markup=links_list_kb(links, site_id))
    await callback.answer()


# ---------------------------------------------------------------------------
# Add Link FSM
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data and c.data.startswith("pl:link:add:"))
async def pl_link_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    site_id = int(callback.data.split(":")[3])
    await state.update_data(site_id=site_id)
    await state.set_state(AddLinkFSM.raw_name)
    await callback.message.edit_text(
        "<b>➕ Новая трекинговая ссылка</b>\n\n"
        "Введите описание в свободной форме:\n"
        "<i>убер польша сторис девушки</i>\n"
        "<i>uber pl reels broad men</i>\n\n"
        "Бот сгенерирует slug автоматически.\n/cancel — отмена"
    )
    await callback.answer()


@router.message(lambda m: m.text and m.text.strip() == "/cancel", AddLinkFSM.raw_name)
@router.message(lambda m: m.text and m.text.strip() == "/cancel", AddLinkFSM.confirm)
async def pl_link_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_kb())


@router.message(AddLinkFSM.raw_name)
async def pl_link_add_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.text or not message.text.strip():
        await message.answer("Введите описание текстом.")
        return
    raw = message.text.strip()
    parsed = parse_preland_input(raw)
    slug = await generate_unique_slug(session, parsed.slug_base)
    data = await state.get_data()
    site_id = data["site_id"]
    site = await get_site_by_id(session, site_id)
    base_url = site.base_url if site else ""
    final_url = f"{base_url.rstrip('/')}/?pl={slug}"
    await state.update_data(
        raw=raw,
        display_name=parsed.display_name,
        slug=slug,
        country=getattr(parsed, "country", None),
        placement=getattr(parsed, "placement", None),
        audience=getattr(parsed, "audience", None),
    )
    await state.set_state(AddLinkFSM.confirm)
    await message.answer(
        f"<b>📋 Предпросмотр ссылки</b>\n\n"
        f"<b>Название:</b> {escape(parsed.display_name)}\n"
        f"<b>Slug:</b> <code>{escape(slug)}</code>\n"
        f"<b>URL для рекламы:</b>\n<code>{escape(final_url)}</code>\n\n"
        "Всё верно?",
        reply_markup=link_confirm_kb(),
    )


@router.callback_query(lambda c: c.data == "pl:link:do_create", AddLinkFSM.confirm)
async def pl_link_do_create(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    from app.services.preland_link_service import create_link
    data = await state.get_data()
    site_id = data["site_id"]
    site = await get_site_by_id(session, site_id)
    if not site:
        await state.clear()
        await callback.answer("Сайт не найден.", show_alert=True)
        return
    try:
        link = await create_link(
            session,
            site=site,
            display_name=data["display_name"],
            slug=data["slug"],
            country=data.get("country"),
            placement=data.get("placement"),
            audience=data.get("audience"),
        )
        await state.clear()
        await callback.message.edit_text(
            f"<b>✅ Ссылка создана!</b>\n\n"
            f"<b>Название:</b> {escape(link.display_name)}\n"
            f"<b>URL для рекламы:</b>\n<code>{escape(link.final_url)}</code>",
            reply_markup=link_card_kb(link.id, site_id),
        )
    except Exception as exc:
        await state.clear()
        await callback.message.edit_text(
            f"Ошибка: {escape(str(exc))}",
            reply_markup=site_card_kb(site_id),
        )
    await callback.answer()


@router.callback_query(lambda c: c.data == "pl:link:reenter", AddLinkFSM.confirm)
async def pl_link_reenter(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddLinkFSM.raw_name)
    await callback.message.edit_text(
        "<b>✏️ Введите название заново</b>\n\n"
        "Пример: <code>uber pl story girls</code>\n/cancel — отмена"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "pl:link:cancel", AddLinkFSM.confirm)
async def pl_link_confirm_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    site_id = data.get("site_id")
    await state.clear()
    if site_id:
        await callback.message.edit_text("Отменено.", reply_markup=site_card_kb(site_id))
    else:
        await callback.message.edit_text("Отменено.", reply_markup=prelands_menu_kb())
    await callback.answer()


# ---------------------------------------------------------------------------
# Link card
# ---------------------------------------------------------------------------

@router.callback_query(lambda c: c.data and c.data.startswith("pl:link:") and c.data[8:].isdigit())
async def pl_link_card(callback: CallbackQuery, session: AsyncSession) -> None:
    link_id = int(callback.data.split(":")[2])
    link = await get_link_by_id(session, link_id)
    if not link:
        await callback.answer("Ссылка не найдена.", show_alert=True)
        return
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    s = await get_link_stats(session, link_id, date_from=today)
    text = (
        f"<b>🔗 {escape(link.display_name)}</b>\n"
        f"<code>{escape(link.final_url)}</code>\n\n"
        f"Сегодня: 👁 {s['visits']} | 👆 {s['clicks']} | CTR {s['ctr']}%"
    )
    await callback.message.edit_text(text, reply_markup=link_card_kb(link_id, link.site_id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("pl:link:stats:"))
async def pl_link_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    parts = callback.data.split(":")
    link_id = int(parts[3])
    period = parts[4] if len(parts) > 4 else "7d"
    link = await get_link_by_id(session, link_id)
    if not link:
        await callback.answer("Ссылка не найдена.", show_alert=True)
        return
    now = datetime.utcnow()
    if period == "today":
        date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_label = "Сегодня"
    elif period == "30d":
        date_from = now - timedelta(days=30)
        period_label = "30 дней"
    elif period == "hourly":
        date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_label = "По часам (сегодня)"
        rows = await get_link_hourly_stats(session, link_id, date_from)
        if rows:
            lines = "\n".join(
                f"  {r['hour']:02d}:00 — 👁{r['views']} 👆{r['clicks']} {r['ctr']}%"
                for r in rows
            )
        else:
            lines = "  нет данных"
        text = (
            f"<b>📊 {escape(link.display_name)} — {period_label}</b>\n\n"
            f"{lines}"
        )
        await callback.message.edit_text(text, reply_markup=link_stats_period_kb(link_id))
        await callback.answer()
        return
    else:
        date_from = now - timedelta(days=7)
        period_label = "7 дней"
    s = await get_link_stats(session, link_id, date_from=date_from)
    text = (
        f"<b>📊 {escape(link.display_name)} — {period_label}</b>\n\n"
        f"👁 Просмотры: {s['visits']}\n"
        f"👆 Клики: {s['clicks']}\n"
        f"CTR: {s['ctr']}%"
    )
    await callback.message.edit_text(text, reply_markup=link_stats_period_kb(link_id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("pl:link:archive:"))
async def pl_link_archive(callback: CallbackQuery, session: AsyncSession) -> None:
    link_id = int(callback.data.split(":")[3])
    link = await get_link_by_id(session, link_id)
    if not link:
        await callback.answer("Ссылка не найдена.", show_alert=True)
        return
    site_id = link.site_id
    await archive_link(session, link)
    links = await list_links_for_site(session, site_id)
    await callback.message.edit_text(
        f"<b>📦 Архивировано: {escape(link.display_name)}</b>",
        reply_markup=links_list_kb(links, site_id),
    )
    await callback.answer("Архивировано.")


@router.callback_query(lambda c: c.data and c.data.startswith("pl:link:check:"))
async def pl_link_check(callback: CallbackQuery, session: AsyncSession) -> None:
    link_id = int(callback.data.split(":")[3])
    link = await get_link_by_id(session, link_id)
    if not link:
        await callback.answer("Ссылка не найдена.", show_alert=True)
        return
    events = await get_link_recent_events(session, link_id, limit=10)
    if not events:
        text = (
            f"<b>🔍 Проверка трекинга: {escape(link.display_name)}</b>\n\n"
            "❌ События не обнаружены.\n\n"
            "<b>Убедитесь, что:</b>\n"
            "1. Скрипт вставлен в HTML сайта перед &lt;/body&gt;\n"
            "2. Открыли финальную ссылку с <code>?pl=</code>\n"
            "3. Бэкенд доступен"
        )
    else:
        lines = []
        for ev in events:
            icon = "👁" if ev["type"] == "page_view" else "👆"
            btn = f" [{ev['button_id']}]" if ev["button_id"] else ""
            ts = ev["created_at"].strftime("%H:%M:%S")
            vid = ev["visitor_id"] or "—"
            lines.append(f"{icon}{btn} {ts} vid:{vid}")
        text = (
            f"<b>🔍 Последние события: {escape(link.display_name)}</b>\n\n"
            + "\n".join(lines)
            + "\n\n✅ Трекинг работает!"
        )
    await callback.message.edit_text(text, reply_markup=link_card_kb(link_id, link.site_id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("pl:link:code:"))
async def pl_link_code(callback: CallbackQuery, session: AsyncSession) -> None:
    parts = callback.data.split(":")
    link_id = int(parts[3])
    # optional: clicks mode from data — pl:link:code:{id}:clicks / :noclick
    clicks_mode = parts[4] if len(parts) > 4 else "clicks"
    track_clicks = (clicks_mode != "noclick")

    link = await get_link_by_id(session, link_id)
    if not link:
        await callback.answer("Ссылка не найдена.", show_alert=True)
        return
    # Inline script with slug baked in — no external load, works always
    js_code = generate_tracking_script(slug=link.slug, track_clicks=track_clicks)
    inline_tag = f"<script>\n{js_code}\n</script>"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    mode_btn = InlineKeyboardButton(
        text="✅ Клики ON" if track_clicks else "☑️ Только просмотры",
        callback_data=f"pl:link:code:{link_id}:{'noclick' if track_clicks else 'clicks'}"
    )
    kb_rows = link_card_kb(link_id, link.site_id).inline_keyboard
    # prepend mode toggle row
    new_kb = InlineKeyboardMarkup(inline_keyboard=[[mode_btn]] + kb_rows)

    text = (
        f"<b>📜 Код для: {escape(link.display_name)}</b>\n\n"
        "<b>1. Вставьте перед &lt;/body&gt; в HTML:</b>\n"
        f"<pre>{escape(inline_tag)}</pre>\n\n"
        "<b>2. Ссылка для рекламы:</b>\n"
        f"<code>{escape(link.final_url)}</code>\n\n"
        + (
            "💡 Ссылки на Telegram/WhatsApp трекаются <b>автоматически</b>.\n"
            'Кастомные кнопки: <code>data-track-click="cta"</code>\n\n'
            if track_clicks else
            "ℹ️ Режим: только просмотры. Клики не трекаются.\n\n"
        )
        + "Переключи режим кнопкой выше."
    )
    await callback.message.edit_text(text, reply_markup=new_kb)
    await callback.answer()

