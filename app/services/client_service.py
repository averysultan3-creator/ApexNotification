from __future__ import annotations

import json
from datetime import datetime, time
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client, ClientStatus
from app.models.lead import Lead
from app.models.facebook_lead_form import FacebookLeadForm
from app.utils.formatters import dump_json, load_json_list


async def create_client(
    session: AsyncSession,
    name: str,
    telegram_ids: list[int | str] | None = None,
    emails: list[str] | None = None,
    notes: str | None = None,
) -> Client:
    client = Client(
        name=name.strip(),
        telegram_ids_json=dump_json([str(item) for item in (telegram_ids or [])]),
        emails_json=dump_json([item.strip() for item in (emails or []) if item.strip()]),
        notes=notes,
        status=ClientStatus.active.value,
    )
    session.add(client)
    await session.flush()
    await session.refresh(client)
    return client


async def get_client_by_id(session: AsyncSession, client_id: int) -> Optional[Client]:
    return (await session.execute(select(Client).where(Client.id == client_id))).scalar_one_or_none()


async def list_clients(session: AsyncSession, active_only: bool = False) -> list[Client]:
    stmt = select(Client).order_by(Client.name)
    if active_only:
        stmt = stmt.where(Client.status == ClientStatus.active.value)
    return list((await session.execute(stmt)).scalars().all())


async def search_clients(session: AsyncSession, query: str) -> list[Client]:
    pattern = f"%{query.strip()}%"
    stmt = select(Client).where(or_(Client.name.ilike(pattern), Client.emails_json.ilike(pattern))).order_by(Client.name)
    return list((await session.execute(stmt)).scalars().all())


async def add_client_telegram_id(session: AsyncSession, client_id: int, telegram_id: int | str) -> Client | None:
    client = await get_client_by_id(session, client_id)
    if not client:
        return None
    values = [str(item) for item in load_json_list(client.telegram_ids_json)]
    value = str(telegram_id).strip()
    if value and value not in values:
        values.append(value)
    client.telegram_ids_json = json.dumps(values, ensure_ascii=False)
    await session.flush()
    await session.refresh(client)
    return client


async def add_client_email(session: AsyncSession, client_id: int, email: str) -> Client | None:
    client = await get_client_by_id(session, client_id)
    if not client:
        return None
    values = [str(item) for item in load_json_list(client.emails_json)]
    value = email.strip()
    if value and value not in values:
        values.append(value)
    client.emails_json = json.dumps(values, ensure_ascii=False)
    await session.flush()
    await session.refresh(client)
    return client


async def toggle_client_status(session: AsyncSession, client_id: int) -> Client | None:
    client = await get_client_by_id(session, client_id)
    if not client:
        return None
    client.status = ClientStatus.inactive.value if client.status == ClientStatus.active.value else ClientStatus.active.value
    await session.flush()
    await session.refresh(client)
    return client


async def get_client_counts(session: AsyncSession, client_id: int) -> tuple[int, int]:
    today = datetime.combine(datetime.utcnow().date(), time.min)
    forms_count = (
        await session.execute(select(func.count()).select_from(FacebookLeadForm).where(FacebookLeadForm.client_id == client_id))
    ).scalar_one()
    leads_today = (
        await session.execute(select(func.count()).select_from(Lead).where(Lead.client_id == client_id, Lead.created_at >= today))
    ).scalar_one()
    return int(forms_count), int(leads_today)
