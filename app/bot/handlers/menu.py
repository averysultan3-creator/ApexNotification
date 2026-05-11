from __future__ import annotations
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.client import show_cabinet
from app.bot.keyboards.funnel_kb import funnel_join_notify_kb
from app.bot.keyboards.main_kb import main_menu_kb
from app.services.admin_service import add_admin, is_admin as check_is_admin
from app.services.client_recipient_service import get_or_create_recipient
from app.services.funnel_form_service import get_form_by_join_code
from app.services.google_sheet_service import send_old_leads_to_recipient
from app.services.lead_service import list_leads_by_funnel
from app.services.stats_service import dashboard_today
from app.utils.formatters import format_dashboard
from config import ADMIN_IDS, ADMIN_SETUP_CODE

router = Router(name="menu")


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession, is_admin: bool = False) -> None:
    args = message.text.split(maxsplit=1)[1] if message.text and " " in message.text else ""

    # /start join_{form_id}_{join_code}
    if args.startswith("join_"):
        parts = args[5:].split("_", 1)
        if len(parts) == 2:
            try:
                form_id = int(parts[0])
                join_code = parts[1]
            except ValueError:
                form_id = None
                join_code = None
            if form_id and join_code:
                form = await get_form_by_join_code(session, form_id, join_code)
                if form:
                    user = message.from_user
                    recipient, is_new, is_reactivation = await get_or_create_recipient(
                        session,
                        funnel_form_id=form.id,
                        telegram_user_id=user.id,
                        telegram_username=user.username,
                        first_name=user.first_name,
                    )
                    if is_new:
                        # Show success message to client (no tag shown)
                        await message.answer(
                            "✅ <b>Подключено!</b>\n\n"
                            f"Воронка: <b>{form.form_name}</b>\n\n"
                            "Теперь вы будете получать новые заявки автоматически."
                        )
                        # Auto-send all old leads to this new recipient
                        # force=True for re-activations: delivery history already exists
                        try:
                            old_leads = await list_leads_by_funnel(session, form.id)
                            if old_leads:
                                sent, _skipped = await send_old_leads_to_recipient(
                                    session, message.bot, recipient, old_leads,
                                    force=is_reactivation, delay=0.15
                                )
                                if sent:
                                    await message.answer(
                                        f"\ud83d\udce6 \u0414\u043e\u0441\u0442\u0430\u0432\u043b\u0435\u043d\u043e \u0430\u0440\u0445\u0438\u0432\u043d\u044b\u0445 \u0437\u0430\u044f\u0432\u043e\u043a: <b>{sent}</b>"
                                    )
                        except Exception:
                            pass
                        # Notify admins
                        uname = f"@{user.username}" if user.username else (user.full_name or str(user.id))
                        for admin_id in ADMIN_IDS:
                            try:
                                await message.bot.send_message(
                                    admin_id,
                                    f"\ud83d\udc65 <b>\u041d\u043e\u0432\u044b\u0439 \u043f\u043e\u043b\u0443\u0447\u0430\u0442\u0435\u043b\u044c</b>\n\n"
                                    f"\u0412\u043e\u0440\u043e\u043d\u043a\u0430: <b>{form.form_name}</b>\n"
                                    f"Telegram: {uname}\n"
                                    f"ID: <code>{user.id}</code>",
                                    reply_markup=funnel_join_notify_kb(form.id, recipient.id),
                                )
                            except Exception:
                                pass
                    else:
                        await message.answer(
                            f"\u2139\ufe0f \u0412\u044b \u0443\u0436\u0435 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u044b \u043a \u0432\u043e\u0440\u043e\u043d\u043a\u0435 <b>{form.form_name}</b>"
                        )
                    # After join, show client cabinet
                    await show_cabinet(message, session)
                    return
                else:
                    await message.answer("❌ Ссылка недействительна или воронка остановлена.")
                    return

    # Route by role
    if is_admin:
        data = await dashboard_today(session)
        await message.answer(format_dashboard(data), reply_markup=main_menu_kb())
    else:
        await show_cabinet(message, session)


@router.callback_query(lambda c: c.data == "main:menu")
async def main_menu(callback: CallbackQuery, session: AsyncSession, is_admin: bool = False) -> None:
    if is_admin:
        data = await dashboard_today(session)
        try:
            await callback.message.edit_text(format_dashboard(data), reply_markup=main_menu_kb())
        except Exception:
            await callback.message.answer(format_dashboard(data), reply_markup=main_menu_kb())
    else:
        await show_cabinet(callback, session)
    await callback.answer()


@router.message(Command("admin"))
@router.message(lambda m: m.text and m.text.strip().lower().startswith("/admin") and len(m.text.strip()) > 6)
async def admin_setup(message: Message, session: AsyncSession) -> None:
    """
    /adminCODE or /admin CODE — grant admin rights via setup code.
    Works even when ADMIN_IDS is empty.
    """
    raw = (message.text or "").split("@")[0].strip()
    if " " in raw:
        args = raw.split(maxsplit=1)[1].strip()
    else:
        args = raw[len("/admin"):]

    if not args:
        await message.answer("Введите admin-код: /admin1234")
        return

    if args != ADMIN_SETUP_CODE:
        await message.answer("Неверный admin-код.")
        return

    user = message.from_user
    admin, is_new = await add_admin(
        session,
        telegram_user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )

    if is_new:
        await message.answer("✅ Готово. Вы теперь администратор.")
    else:
        await message.answer("ℹ️ Вы уже администратор.")

    # Show admin dashboard
    data = await dashboard_today(session)
    await message.answer(format_dashboard(data), reply_markup=main_menu_kb())

