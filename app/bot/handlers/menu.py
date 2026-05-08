from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.main_kb import main_menu_kb
from app.services.stats_service import dashboard_today
from app.utils.formatters import format_dashboard

router = Router(name="menu")


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession) -> None:
    data = await dashboard_today(session)
    await message.answer(format_dashboard(data), reply_markup=main_menu_kb())


@router.callback_query(lambda c: c.data == "main:menu")
async def main_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    data = await dashboard_today(session)
    await callback.message.edit_text(format_dashboard(data), reply_markup=main_menu_kb())
    await callback.answer()
