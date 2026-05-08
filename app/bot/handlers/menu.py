from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.main_kb import main_menu_kb
from app.bot.keyboards.clients_kb import client_card_kb
from app.services.stats_service import dashboard_today
from app.services.client_service import add_telegram_id, get_client_by_id
from app.utils.formatters import format_dashboard
from config import ADMIN_IDS

router = Router(name="menu")


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession) -> None:
    # Deep link: /start reg_<client_id>
    args = message.text.split(maxsplit=1)[1] if message.text and " " in message.text else ""
    if args.startswith("reg_"):
        try:
            client_id = int(args[4:])
        except ValueError:
            client_id = None
        if client_id:
            client = await get_client_by_id(session, client_id)
            if client:
                await add_telegram_id(session, client, message.from_user.id)
                await message.answer(
                    f"✅ Готово! Теперь ты получаешь уведомления о лидах клиента <b>{client.name}</b>.\n\n"
                    f"Твой Telegram ID: <code>{message.from_user.id}</code>"
                )
                # Notify admins
                for admin_id in ADMIN_IDS:
                    if admin_id != message.from_user.id:
                        try:
                            await message.bot.send_message(
                                admin_id,
                                f"👤 <b>{message.from_user.full_name}</b> (@{message.from_user.username or '—'}) "
                                f"подписался на уведомления клиента <b>{client.name}</b>\n"
                                f"ID: <code>{message.from_user.id}</code>",
                            )
                        except Exception:
                            pass
                return
            else:
                await message.answer("❌ Ссылка недействительна.")
                return

    data = await dashboard_today(session)
    await message.answer(format_dashboard(data), reply_markup=main_menu_kb())


@router.callback_query(lambda c: c.data == "main:menu")
async def main_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    data = await dashboard_today(session)
    await callback.message.edit_text(format_dashboard(data), reply_markup=main_menu_kb())
    await callback.answer()
