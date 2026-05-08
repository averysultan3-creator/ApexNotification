from __future__ import annotations
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.client import Client, ClientStatus
from app.utils.formatters import load_json_list


async def create_client(session: AsyncSession, *, name: str) -> Client:
    client = Client(name=name.strip())
    session.add(client)
    await session.flush()
    await session.refresh(client)
    return client


async def get_client_by_id(session: AsyncSession, client_id: int) -> Client | None:
    return (await session.execute(
        select(Client).where(Client.id == client_id)
    )).scalar_one_or_none()


async def list_clients(session: AsyncSession, active_only: bool = False) -> list[Client]:
    stmt = select(Client).order_by(Client.created_at.desc())
    if active_only:
        stmt = stmt.where(Client.status == ClientStatus.active.value)
    return list((await session.execute(stmt)).scalars().all())


async def add_telegram_id(session: AsyncSession, client: Client, telegram_id: int | str) -> Client:
    ids = load_json_list(client.telegram_ids_json)
    tid = str(telegram_id)
    if tid not in ids:
        ids.append(tid)
        client.telegram_ids_json = json.dumps(ids)
        await session.flush()
    return client


async def remove_telegram_id(session: AsyncSession, client: Client, telegram_id: int | str) -> Client:
    ids = load_json_list(client.telegram_ids_json)
    tid = str(telegram_id)
    if tid in ids:
        ids.remove(tid)
        client.telegram_ids_json = json.dumps(ids)
        await session.flush()
    return client


async def set_google_sheet(
    session: AsyncSession, client: Client, sheet_id: str, sheet_name: str = "Sheet1"
) -> Client:
    client.google_sheet_id = sheet_id.strip() or None
    client.google_sheet_name = sheet_name.strip() or "Sheet1"
    await session.flush()
    return client


async def toggle_client_status(session: AsyncSession, client_id: int) -> Client | None:
    client = await get_client_by_id(session, client_id)
    if not client:
        return None
    client.status = (
        ClientStatus.inactive.value
        if client.status == ClientStatus.active.value
        else ClientStatus.active.value
    )
    await session.flush()
    return client
