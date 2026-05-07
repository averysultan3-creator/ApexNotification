import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin_kb import (
    MenuCb, main_menu_kb, clients_section_kb, offers_section_kb,
    forms_section_kb, leads_section_kb, stats_section_kb, export_section_kb,
    back_to_menu_kb, conversions_menu_kb, refs_global_kb,
    settings_kb, roles_list_kb, role_user_view_kb, role_select_kb,
    RoleCb,
)
from services.referral_service import get_all_refs
from services.today_service import get_leads_by_status_today
from services.user_service import (
    list_bot_users, get_bot_user_by_id, create_bot_user,
    update_bot_user, toggle_bot_user, delete_bot_user,
)
from states.wizard_states import CreateBotUserFSM
from models.referral_source_stats_daily import ReferralSourceStatsDaily
from sqlalchemy import select, func, and_
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = Router()

MAIN_MENU_TEXT = (
    "🏠 <b>ApexNotification</b>\n\n"
    "Выберите раздел:"
)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@router.callback_query(MenuCb.filter(F.section == "main"))
async def go_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(MAIN_MENU_TEXT, reply_markup=main_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(MenuCb.filter(F.section == "clients"))
async def menu_clients(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "👥 <b>Клиенты</b>\n\nВыберите действие:",
        reply_markup=clients_section_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(MenuCb.filter(F.section == "offers"))
async def menu_offers(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📦 <b>Офферы</b>\n\nВыберите действие:",
        reply_markup=offers_section_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(MenuCb.filter(F.section == "forms"))
async def menu_forms(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📝 <b>Лидформы</b>\n\nВыберите действие:",
        reply_markup=forms_section_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(MenuCb.filter(F.section == "leads"))
async def menu_leads(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📥 <b>Лиды</b>\n\nВыберите действие:",
        reply_markup=leads_section_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(MenuCb.filter(F.section == "stats"))
async def menu_stats(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📊 <b>Статистика</b>\n\nВыберите тип:",
        reply_markup=stats_section_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(MenuCb.filter(F.section == "export"))
async def menu_export(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📤 <b>Экспорт лидов</b>\n\nВыберите формат:",
        reply_markup=export_section_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(MenuCb.filter(F.section == "settings"))
async def menu_settings(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\nВыберите раздел:",
        reply_markup=settings_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
# Role management
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(RoleCb.filter(F.action == "list"))
async def roles_list(callback: CallbackQuery, session: AsyncSession) -> None:
    users = await list_bot_users(session)
    await callback.message.edit_text(
        f"👥 <b>Пользователи и роли</b>\n\nВсего: {len(users)}",
        reply_markup=roles_list_kb(users),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(RoleCb.filter(F.action == "view"))
async def role_user_view(callback: CallbackQuery, callback_data: RoleCb, session: AsyncSession) -> None:
    user = await get_bot_user_by_id(session, callback_data.uid)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    status = "✅ Активен" if user.is_active else "⏸ Отключён"
    text = (
        f"👤 <b>Пользователь #{user.id}</b>\n\n"
        f"TG ID: <code>{user.telegram_user_id}</code>\n"
        f"Username: @{user.telegram_username or '—'}\n"
        f"Роль: <b>{user.role}</b>\n"
        f"Клиент: {user.client_id or '—'}\n"
        f"Статус: {status}\n"
        f"Заметки: {user.notes or '—'}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=role_user_view_kb(user.id, user.is_active),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(RoleCb.filter(F.action == "toggle"))
async def role_toggle(callback: CallbackQuery, callback_data: RoleCb, session: AsyncSession) -> None:
    user = await get_bot_user_by_id(session, callback_data.uid)
    if not user:
        await callback.answer("Не найден", show_alert=True)
        return
    await toggle_bot_user(session, user.id)
    await session.commit()
    await callback.answer("Статус изменён")
    view_cb = RoleCb(action="view", uid=callback_data.uid)
    await role_user_view(callback, view_cb, session)


@router.callback_query(RoleCb.filter(F.action == "delete"))
async def role_delete(callback: CallbackQuery, callback_data: RoleCb, session: AsyncSession) -> None:
    await delete_bot_user(session, callback_data.uid)
    await session.commit()
    await callback.answer("Удалено")
    users = await list_bot_users(session)
    await callback.message.edit_text(
        f"🗑 Пользователь удалён.\n\n👥 <b>Пользователи и роли</b>\n\nВсего: {len(users)}",
        reply_markup=roles_list_kb(users),
        parse_mode="HTML",
    )


@router.callback_query(RoleCb.filter(F.action == "add"))
async def role_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreateBotUserFSM.waiting_tg_id)
    await callback.message.edit_text(
        "👤 <b>Добавить пользователя</b>\n\nВведи Telegram ID (число):\n"
        "<i>Можно узнать через @userinfobot</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateBotUserFSM.waiting_tg_id)
async def role_add_tg_id(message: Message, state: FSMContext) -> None:
    raw = message.text.strip() if message.text else ""
    if not raw.lstrip("-").isdigit():
        await message.answer("❌ Нужно ввести числовой Telegram ID:")
        return
    await state.update_data({"_new_user_tg_id": int(raw)})
    await state.set_state(CreateBotUserFSM.select_role)
    await message.answer(
        f"ID: <code>{raw}</code>\n\nВыбери роль:",
        reply_markup=role_select_kb(),
        parse_mode="HTML",
    )


@router.callback_query(RoleCb.filter(F.action == "set_role"), CreateBotUserFSM.select_role)
async def role_set(callback: CallbackQuery, callback_data: RoleCb, state: FSMContext, session: AsyncSession) -> None:
    from models.bot_user import ROLES
    page = callback_data.page  # 0=super_admin, 1=client_admin, 2=client_viewer, 3=manager
    if page >= len(ROLES):
        await callback.answer("Неверная роль", show_alert=True)
        return
    role = ROLES[page]
    data = await state.get_data()
    tg_id = data.get("_new_user_tg_id")
    if not tg_id:
        await callback.answer("Ошибка: нет TG ID", show_alert=True)
        await state.clear()
        return
    user = await create_bot_user(
        session, tg_id=tg_id, username=None, role=role,
    )
    await session.commit()
    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>Пользователь добавлен</b>\n\n"
        f"TG ID: <code>{tg_id}</code>\n"
        f"Роль: <b>{role}</b>",
        reply_markup=roles_list_kb(await list_bot_users(session)),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(MenuCb.filter(F.section == "conv"))
async def menu_conv(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📈 <b>Конверсии и аналитика</b>\n\nВыберите раздел:",
        reply_markup=conversions_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(MenuCb.filter(F.section == "refs"))
async def menu_refs(callback: CallbackQuery, session: AsyncSession) -> None:
    """Global sources list with today's mini-metrics."""
    today = _today()
    refs = await get_all_refs(session)

    # Load today's aggregated stats per ref in one query
    stats_q = select(
        ReferralSourceStatsDaily.referral_source_id,
        func.sum(ReferralSourceStatsDaily.bot_starts).label("starts"),
        func.sum(ReferralSourceStatsDaily.leads_created).label("leads"),
        func.sum(ReferralSourceStatsDaily.approved).label("approved"),
    ).where(
        and_(
            ReferralSourceStatsDaily.date == today,
            ReferralSourceStatsDaily.referral_source_id.isnot(None),
        )
    ).group_by(ReferralSourceStatsDaily.referral_source_id)
    stats_rows = (await session.execute(stats_q)).all()
    stats_map = {
        row.referral_source_id: (int(row.leads or 0), int(row.approved or 0), int(row.starts or 0))
        for row in stats_rows
    }

    refs_stats = [
        (ref, *stats_map.get(ref.id, (0, 0, 0)))
        for ref in refs
    ]

    count = len(refs)
    text = (
        f"🔗 <b>Источники</b> (всего: {count})\n\n"
        f"📅 Метрики: сегодня  |  L=лиды, A=approved\n"
        f"🟢 ≥15% approved  🟡 5-15%  🔴 &lt;5%  ⚫ мало данных"
    )
    if not refs:
        text += "\n\n<i>Источников пока нет.</i>"

    await callback.message.edit_text(
        text,
        reply_markup=refs_global_kb(refs_stats),
        parse_mode="HTML",
    )
    await callback.answer()
