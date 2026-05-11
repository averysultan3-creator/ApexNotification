from __future__ import annotations
import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.client_recipient import ClientRecipient, RecipientStatus

logger = logging.getLogger(__name__)


async def get_or_create_recipient(
    session: AsyncSession,
    funnel_form_id: int,
    telegram_user_id: int,
    telegram_username: str | None = None,
    first_name: str | None = None,
) -> tuple[ClientRecipient, bool]:
    existing = (await session.execute(
        select(ClientRecipient).where(
            ClientRecipient.funnel_form_id == funnel_form_id,
            ClientRecipient.telegram_user_id == telegram_user_id,
        )
    )).scalar_one_or_none()
    if existing:
        if existing.status != RecipientStatus.active.value:
            # Re-activating a previously removed recipient — treat as new so old leads are sent
            existing.status = RecipientStatus.active.value
            if telegram_username:
                existing.telegram_username = telegram_username
            if first_name:
                existing.first_name = first_name
            await session.flush()
            return existing, True  # is_new=True → triggers old leads delivery
        return existing, False
    recipient = ClientRecipient(
        funnel_form_id=funnel_form_id,
        telegram_user_id=telegram_user_id,
        telegram_username=telegram_username,
        first_name=first_name,
        status=RecipientStatus.active.value,
    )
    session.add(recipient)
    await session.flush()
    await session.refresh(recipient)
    return recipient, True


async def list_recipients(session: AsyncSession, funnel_form_id: int) -> list[ClientRecipient]:
    result = await session.execute(
        select(ClientRecipient).where(
            ClientRecipient.funnel_form_id == funnel_form_id,
            ClientRecipient.status == RecipientStatus.active.value,
        ).order_by(ClientRecipient.joined_at)
    )
    return list(result.scalars().all())


async def remove_recipient(session: AsyncSession, recipient_id: int) -> bool:
    r = (await session.execute(
        select(ClientRecipient).where(ClientRecipient.id == recipient_id)
    )).scalar_one_or_none()
    if r:
        r.status = RecipientStatus.disabled.value
        await session.flush()
        return True
    return False


async def send_leads_to_recipient(
    bot,
    recipient: ClientRecipient,
    leads: list,
    *,
    delay: float = 0.3,
) -> tuple[int, int]:
    sent = 0
    errors = 0
    from app.utils.formatters import format_lead_notification
    for lead in leads:
        try:
            await bot.send_message(recipient.telegram_user_id, format_lead_notification(lead))
            sent += 1
            if delay:
                await asyncio.sleep(delay)
        except Exception as e:
            logger.warning("send_leads_to_recipient tg=%s lead=%s: %s", recipient.telegram_user_id, lead.id, e)
            errors += 1
    return sent, errors
