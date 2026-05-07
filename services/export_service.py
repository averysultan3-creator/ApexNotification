import csv
import io
import json
from typing import Optional, Dict, Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.lead import Lead


async def _fetch_leads(
    session: AsyncSession, filters: Optional[Dict[str, Any]] = None
) -> List[Lead]:
    q = select(Lead)
    if filters:
        if filters.get("client_id"):
            q = q.where(Lead.client_id == int(filters["client_id"]))
        if filters.get("offer_id"):
            q = q.where(Lead.offer_id == int(filters["offer_id"]))
        if filters.get("form_id"):
            q = q.where(Lead.form_id == int(filters["form_id"]))
        if filters.get("ref_id"):
            q = q.where(Lead.referral_source_id == int(filters["ref_id"]))
        if filters.get("status"):
            q = q.where(Lead.status == filters["status"])
        if filters.get("date_from"):
            q = q.where(Lead.created_at >= filters["date_from"])
        if filters.get("date_to"):
            q = q.where(Lead.created_at <= filters["date_to"])
    q = q.order_by(Lead.created_at.desc())
    result = await session.execute(q)
    return list(result.scalars().all())


def _lead_to_row(lead: Lead) -> List[str]:
    answers_raw = lead.answers_json or "{}"
    try:
        answers: dict = json.loads(answers_raw)
    except Exception:
        answers = {}
    answers_str = "; ".join(f"{k}: {v}" for k, v in answers.items())

    client_name = lead.client.name if lead.client else ""
    offer_name = lead.offer.name if lead.offer else ""
    form_name = lead.form.name if lead.form else ""
    ref_name = lead.referral_source.name if lead.referral_source else ""

    return [
        str(lead.id),
        str(lead.telegram_user_id),
        lead.telegram_username or "",
        lead.first_name or "",
        lead.last_name or "",
        client_name,
        offer_name,
        form_name,
        ref_name,
        answers_str,
        lead.status,
        lead.admin_notes or "",
        lead.created_at.strftime("%Y-%m-%d %H:%M:%S") if lead.created_at else "",
    ]


_HEADERS = [
    "ID", "TG User ID", "Username", "First Name", "Last Name",
    "Client", "Offer", "Form", "Ref Source",
    "Answers", "Status", "Admin Notes", "Created At",
]


async def export_leads_csv(
    session: AsyncSession, filters: Optional[Dict[str, Any]] = None
) -> bytes:
    leads = await _fetch_leads(session, filters)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(_HEADERS)
    for lead in leads:
        writer.writerow(_lead_to_row(lead))
    return output.getvalue().encode("utf-8-sig")


async def export_leads_xlsx(
    session: AsyncSession, filters: Optional[Dict[str, Any]] = None
) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    leads = await _fetch_leads(session, filters)
    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"

    ws.append(_HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for lead in leads:
        ws.append(_lead_to_row(lead))

    # Auto-width
    for col in ws.columns:
        max_len = max((len(str(cell.value or "")) for cell in col), default=0)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
