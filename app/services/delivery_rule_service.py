import json
from typing import List, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery_rule import DeliveryRule


async def list_rules(session: AsyncSession) -> List[DeliveryRule]:
    result = await session.execute(select(DeliveryRule).order_by(DeliveryRule.id))
    return list(result.scalars().all())


async def get_rule(session: AsyncSession, rule_id: int) -> Optional[DeliveryRule]:
    result = await session.execute(select(DeliveryRule).where(DeliveryRule.id == rule_id))
    return result.scalar_one_or_none()


async def create_rule(
    session: AsyncSession,
    source_id: int,
    client_id: int | None = None,
    send_to_admin: bool = True,
    telegram_ids: list | None = None,
    emails: list | None = None,
    google_sheet_id: str | None = None,
) -> DeliveryRule:
    rule = DeliveryRule(
        source_type="facebook_form",
        source_id=source_id,
        client_id=client_id,
        send_to_admin=send_to_admin,
        telegram_ids_json=json.dumps(telegram_ids or []),
        emails_json=json.dumps(emails or []),
        google_sheet_id=google_sheet_id,
    )
    session.add(rule)
    await session.flush()
    return rule


async def toggle_admin(session: AsyncSession, rule_id: int) -> DeliveryRule:
    rule = await get_rule(session, rule_id)
    rule.send_to_admin = not rule.send_to_admin
    await session.flush()
    return rule


async def delete_rule(session: AsyncSession, rule_id: int) -> None:
    await session.execute(delete(DeliveryRule).where(DeliveryRule.id == rule_id))
