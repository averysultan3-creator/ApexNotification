from typing import Optional, Tuple, List

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.client import Client, ClientStatus


async def get_clients_paginated(
    session: AsyncSession,
    page: int = 0,
    page_size: int = 10,
    status_filter: Optional[str] = None,
) -> Tuple[List[Client], int]:
    base_q = select(Client)
    if status_filter:
        base_q = base_q.where(Client.status == status_filter)

    count_result = await session.execute(select(func.count()).select_from(base_q.subquery()))
    total = count_result.scalar_one()

    result = await session.execute(
        base_q.order_by(Client.name).offset(page * page_size).limit(page_size)
    )
    items = list(result.scalars().all())
    return items, total


async def get_client_by_id(session: AsyncSession, client_id: int) -> Optional[Client]:
    result = await session.execute(select(Client).where(Client.id == client_id))
    return result.scalar_one_or_none()


async def search_clients(
    session: AsyncSession, query: str, page: int = 0, page_size: int = 10
) -> Tuple[List[Client], int]:
    pattern = f"%{query}%"
    base_q = select(Client).where(
        or_(Client.name.ilike(pattern), Client.telegram_username.ilike(pattern))
    )
    count_result = await session.execute(select(func.count()).select_from(base_q.subquery()))
    total = count_result.scalar_one()
    result = await session.execute(
        base_q.order_by(Client.name).offset(page * page_size).limit(page_size)
    )
    return list(result.scalars().all()), total


async def create_client(
    session: AsyncSession,
    name: str,
    telegram_username: Optional[str] = None,
    notes: Optional[str] = None,
) -> Client:
    client = Client(
        name=name,
        telegram_username=telegram_username,
        notes=notes,
        status=ClientStatus.active.value,
    )
    session.add(client)
    await session.flush()
    await session.refresh(client)
    return client


async def update_client_field(
    session: AsyncSession, client_id: int, field: str, value: str
) -> Optional[Client]:
    client = await get_client_by_id(session, client_id)
    if not client:
        return None
    allowed = {"name", "telegram_username", "notes"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' is not editable.")
    setattr(client, field, value if value else None)
    await session.flush()
    await session.refresh(client)
    return client


async def toggle_client_status(session: AsyncSession, client_id: int) -> Optional[Client]:
    client = await get_client_by_id(session, client_id)
    if not client:
        return None
    client.status = (
        ClientStatus.inactive.value
        if client.status == ClientStatus.active.value
        else ClientStatus.active.value
    )
    await session.flush()
    await session.refresh(client)
    return client


async def delete_client(session: AsyncSession, client_id: int) -> bool:
    client = await get_client_by_id(session, client_id)
    if not client:
        return False
    await session.delete(client)
    await session.flush()
    return True
