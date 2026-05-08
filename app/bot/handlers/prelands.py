from datetime import datetime, timedelta
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.prelands_kb import preland_card_kb, prelands_list_kb, prelands_menu_kb
from app.bot.states.preland_states import AddPrelandFSM
from app.services.preland_service import (
    create_preland, get_preland_by_id, list_prelands, toggle_preland_status
)
from app.services.preland_tracking_service import get_preland_button_stats, get_preland_stats
from config import PUBLIC_BASE_URL

router = Router(name="prelands")


@router.callback_query(lambda c: c.data == "prelands:menu")
async def prelands_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    prelands = await list_prelands(session, active_only=True)
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    total_v = total_c = 0
    for p in prelands:
        s = await get_preland_stats(session, p.id, date_from=today_start)
        total_v += s["visits"]
        total_c += s["clicks"]
    ctr = round(total_c / total_v * 100, 1) if total_v else 0.0
    text = (
        f"🌐 <b>Prelands</b>\n\n"
        f"Сегодня:\n"
        f"👁 Views: {total_v}\n"
        f"👆 Clicks: {total_c}\n"
        f"📈 CTR: {ctr}%"
    )
    await callback.message.edit_text(text, reply_markup=prelands_menu_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "prelands:add")
async def prelands_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddPrelandFSM.name)
    await callback.message.edit_text("🌐 <b>Добавление прелендинга</b>\n\nШаг 1/3. Название:")
    await callback.answer()


@router.message(AddPrelandFSM.name)
async def prelands_add_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(AddPrelandFSM.slug)
    await message.answer("Шаг 2/3. Slug (латиница, напр. <code>remote-ua</code>):")


@router.message(AddPrelandFSM.slug)
async def prelands_add_slug(message: Message, state: FSMContext) -> None:
    slug = message.text.strip().lower().replace(" ", "-")
    await state.update_data(slug=slug)
    await state.set_state(AddPrelandFSM.url)
    await message.answer("Шаг 3/3. URL (или /skip):")


@router.message(AddPrelandFSM.url)
async def prelands_add_url(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    url = message.text.strip() if message.text.strip() != "/skip" else None
    try:
        preland = await create_preland(session, name=data["name"], slug=data["slug"], url=url)
        await state.clear()
        script = f'<script src="{PUBLIC_BASE_URL}/track/pixel.js?pl={preland.slug}"></script>'
        await message.answer(
            f"✅ <b>{preland.name}</b> добавлен!\n\n"
            f"Slug: <code>{preland.slug}</code>\n\n"
            f"Вставь в &lt;head&gt;:\n<pre>{script}</pre>",
            reply_markup=preland_card_kb(preland.id),
        )
    except Exception as e:
        await state.clear()
        await message.answer(f"❌ Ошибка: {e}")


@router.callback_query(lambda c: c.data == "prelands:list")
async def prelands_list(callback: CallbackQuery, session: AsyncSession) -> None:
    prelands = await list_prelands(session)
    if not prelands:
        await callback.answer("Прелендингов нет.", show_alert=True)
        return
    await callback.message.edit_text("🌐 Список:", reply_markup=prelands_list_kb(prelands))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("prelands:card:"))
async def preland_card(callback: CallbackQuery, session: AsyncSession) -> None:
    preland_id = int(callback.data.split(":")[2])
    p = await get_preland_by_id(session, preland_id)
    if not p:
        await callback.answer("Не найден.", show_alert=True)
        return
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    stats = await get_preland_stats(session, p.id, date_from=today_start)
    btn_stats = await get_preland_button_stats(session, p.id)
    btn_text = "\n".join(f"  {k}: {v}" for k, v in btn_stats.items()) if btn_stats else "  —"
    text = (
        f"🌐 <b>{p.name}</b>\n\n"
        f"Slug: <code>{p.slug}</code>\n"
        f"URL: {p.url or '—'}\n\n"
        f"Сегодня:\n"
        f"Views: {stats['visits']} | Clicks: {stats['clicks']} | CTR: {stats['ctr']}%\n\n"
        f"Кнопки сегодня:\n{btn_text}"
    )
    await callback.message.edit_text(text, reply_markup=preland_card_kb(p.id))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("prelands:code:"))
async def preland_code(callback: CallbackQuery, session: AsyncSession) -> None:
    preland_id = int(callback.data.split(":")[2])
    p = await get_preland_by_id(session, preland_id)
    if not p:
        await callback.answer("Не найден.", show_alert=True)
        return
    script = f'<script src="{PUBLIC_BASE_URL}/track/pixel.js?pl={p.slug}"></script>'
    btn_ex = f'<a href="https://t.me/..." data-track-click="main_cta">Оставить заявку</a>'
    text = (
        f"📎 <b>Код для {p.name}</b>\n\n"
        f"Вставь в &lt;head&gt;:\n<pre>{script}</pre>\n\n"
        f"На кнопку:\n<pre>{btn_ex}</pre>"
    )
    await callback.message.edit_text(text, reply_markup=preland_card_kb(p.id))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("prelands:stats:"))
async def preland_stats_7d(callback: CallbackQuery, session: AsyncSession) -> None:
    preland_id = int(callback.data.split(":")[2])
    p = await get_preland_by_id(session, preland_id)
    if not p:
        await callback.answer("Не найден.", show_alert=True)
        return
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = datetime.now() - timedelta(days=7)
    s1 = await get_preland_stats(session, p.id, date_from=today_start)
    s7 = await get_preland_stats(session, p.id, date_from=week_start)
    text = (
        f"📊 <b>{p.name}</b>\n\n"
        f"Сегодня: 👁{s1['visits']} 👆{s1['clicks']} 📈{s1['ctr']}%\n"
        f"7 дней:   👁{s7['visits']} 👆{s7['clicks']} 📈{s7['ctr']}%"
    )
    await callback.message.edit_text(text, reply_markup=preland_card_kb(p.id))
    await callback.answer()
