from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead


async def export_leads_rows(session: AsyncSession, limit: int = 1000) -> list[list[str]]:
    stmt = select(Lead).order_by(Lead.created_at.desc()).limit(limit)
    leads = list((await session.execute(stmt)).scalars().all())
    rows = [["id", "created_at", "client_id", "fb_form_id", "full_name", "phone", "email", "status"]]
    for lead in leads:
        rows.append(
            [
                str(lead.id),
                lead.created_at.isoformat(sep=" ") if lead.created_at else "",
                str(lead.client_id or ""),
                lead.fb_form_id or "",
                lead.full_name or "",
                lead.phone or "",
                lead.email or "",
                lead.status,
            ]
        )
    return rows
