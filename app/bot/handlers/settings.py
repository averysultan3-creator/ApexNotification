from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.stats_kb import settings_kb
from app.utils.formatters import tracking_code_text, webhook_settings_text
from config import FACEBOOK_VERIFY_TOKEN, PUBLIC_BASE_URL

router = Router(name="settings")


@router.callback_query(lambda c: c.data == "settings:menu")
async def settings_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(webhook_settings_text(), reply_markup=settings_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "settings:webhook")
async def settings_webhook(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🔗 <b>Webhook данные</b>\n\n"
        "Callback URL:\n"
        f"{PUBLIC_BASE_URL}/webhooks/facebook\n\n"
        "Verify Token:\n"
        f"{FACEBOOK_VERIFY_TOKEN}",
        reply_markup=settings_kb(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "settings:tracking")
async def settings_tracking(callback: CallbackQuery) -> None:
    await callback.message.edit_text(tracking_code_text("SLUG"), reply_markup=settings_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "settings:health")
async def settings_health(callback: CallbackQuery) -> None:
    await callback.answer("Health: /health returns {\"status\":\"ok\"}", show_alert=True)


@router.callback_query(lambda c: c.data == "settings:guide")
async def settings_guide(callback: CallbackQuery) -> None:
    text = (
        "📖 <b>Инструкция подключения</b>\n\n"
        "Facebook:\n"
        "1. Meta App → Webhooks.\n"
        "2. Object: Page.\n"
        f"3. Callback URL: {PUBLIC_BASE_URL}/webhooks/facebook\n"
        f"4. Verify Token: {FACEBOOK_VERIFY_TOKEN}\n"
        "5. Subscribe: leadgen.\n"
        "6. Добавь Page Access Token в .env.\n"
        "7. В боте добавь FB Page ID и FB Form ID.\n\n"
        "Preland:\n"
        "1. Вставь tracking script перед </body>.\n"
        "2. На CTA добавь data-track-click=\"main_cta\".\n"
        "3. Открой страницу и проверь visits/clicks/CTR."
    )
    await callback.message.edit_text(text, reply_markup=settings_kb())
    await callback.answer()
