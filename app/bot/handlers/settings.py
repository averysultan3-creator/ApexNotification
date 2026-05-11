from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from config import FACEBOOK_VERIFY_TOKEN, PUBLIC_BASE_URL

router = Router(name="settings")


def _settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f517 Webhook URL", callback_data="settings:webhook")],
        [InlineKeyboardButton(text="\U0001f511 Verify token", callback_data="settings:verify_token")],
        [InlineKeyboardButton(text="\U0001f4cd Код трекинга", callback_data="settings:tracking")],
        [InlineKeyboardButton(text="\U0001f3e5 Статус сервера", callback_data="settings:health")],
        [InlineKeyboardButton(text="\u2b05 Назад", callback_data="main:menu")],
    ])


@router.callback_query(lambda c: c.data == "settings:menu")
async def settings_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text("<b>⚙\ufe0f Настройки</b>", reply_markup=_settings_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "settings:webhook")
async def settings_webhook(callback: CallbackQuery) -> None:
    url = f"{PUBLIC_BASE_URL}/webhooks/facebook"
    await callback.message.edit_text(
        f"<b>Facebook Webhook URL</b>\n\n<code>{url}</code>\n\n"
        "Meta Developer Console → Webhooks → Callback URL",
        reply_markup=_settings_kb(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "settings:verify_token")
async def settings_verify_token(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        f"<b>Verify Token</b>\n\n<code>{FACEBOOK_VERIFY_TOKEN}</code>\n\n"
        "Meta Developer Console → Webhooks → Verify Token",
        reply_markup=_settings_kb(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "settings:tracking")
async def settings_tracking(callback: CallbackQuery) -> None:
    example = (
        f'&lt;script src="{PUBLIC_BASE_URL}/track/pixel.js?pl=YOUR_SLUG"&gt;&lt;/script&gt;\n\n'
        '&lt;a href="..." data-track-click="main_cta"&gt;Оставить заявку&lt;/a&gt;'
    )
    await callback.message.edit_text(
        f"<b>Код трекинга</b>\n\n<pre>{example}</pre>",
        reply_markup=_settings_kb(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "settings:health")
async def settings_health(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        f"<b>Статус сервера</b>\n\n<code>GET {PUBLIC_BASE_URL}/health</code>",
        reply_markup=_settings_kb(),
    )
    await callback.answer()
