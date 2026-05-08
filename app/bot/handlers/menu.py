from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.main_kb import main_menu_kb
from app.bot.keyboards.funnel_kb import funnel_join_notify_kb
from app.services.funnel_form_service import get_form_by_join_code
from app.services.client_recipient_service import get_or_create_recipient, list_recipients
from app.services.stats_service import dashboard_today
from app.utils.formatters import format_dashboard
from config import ADMIN_IDS

router = Router(name="menu")


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession) -> None:
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
                    recipient, is_new = await get_or_create_recipient(
                        session,
                        funnel_form_id=form.id,
                        telegram_user_id=user.id,
                        telegram_username=user.username,
                        first_name=user.first_name,
                    )
                    if is_new:
                        await message.answer(
                            f"✅ <b>Вы подключены!</b>\n\n"
                            f"Теперь вы будете получать заявки по форме:\n"
                            f"<b>{form.form_name}</b>\n\n"
                            f"Тег: {form.tag or '—'}"
                        )
                        # Notify admins
                        uname = f"@{user.username}" if user.username else user.full_name
                        recipients = await list_recipients(session, form.id)
                        for admin_id in ADMIN_IDS:
                            try:
                                await message.bot.send_message(
                                    admin_id,
                                    f"👥 <b>Новый получатель подключён</b>\n\n"
                                    f"Форма: <b>{form.form_name}</b>\n"
                                    f"Пользователь: {uname}\n"
                                    f"Telegram ID: <code>{user.id}</code>\n\n"
                                    f"Отправить ему старые заявки?",
                                    reply_markup=funnel_join_notify_kb(form.id, recipient.id),
                                )
                            except Exception:
                                pass
                    else:
                        await message.answer(
                            f"ℹ️ Вы уже подключены к форме <b>{form.form_name}</b>"
                        )
                    return
                else:
                    await message.answer("❌ Ссылка недействительна или форма выключена.")
                    return

    data = await dashboard_today(session)
    await message.answer(format_dashboard(data), reply_markup=main_menu_kb())


@router.callback_query(lambda c: c.data == "main:menu")
async def main_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    data = await dashboard_today(session)
    await callback.message.edit_text(format_dashboard(data), reply_markup=main_menu_kb())
    await callback.answer()
