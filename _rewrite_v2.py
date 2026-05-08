"""
Apex Lead Router — полный рерайт v2.
Главная сущность — FunnelForm (не Client).
Флоу: форма → клиенты подключаются позже через join-ссылку.
"""
import os, textwrap

ROOT = os.path.dirname(__file__)

def w(path, content):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content).lstrip())
    print(f"  wrote {path}")

# ─────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────

w("app/models/funnel_form.py", """
from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class FunnelFormStatus(str, enum.Enum):
    active = "active"
    disabled = "disabled"


class FunnelForm(Base):
    __tablename__ = "funnel_forms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    form_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    offer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fb_form_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    fb_page_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verify_token: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    join_code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    google_sheet_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    google_sheet_name: Mapped[str] = mapped_column(String(200), nullable=False, default="Leads")
    apps_script_web_app_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=FunnelFormStatus.active.value, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    recipients: Mapped[list["ClientRecipient"]] = relationship(
        "ClientRecipient", back_populates="funnel_form", lazy="selectin",
        foreign_keys="ClientRecipient.funnel_form_id"
    )
    leads: Mapped[list["Lead"]] = relationship(
        "Lead", back_populates="funnel_form", lazy="selectin",
        foreign_keys="Lead.funnel_form_id"
    )

    def __repr__(self) -> str:
        return f"<FunnelForm id={self.id} form_name={self.form_name!r}>"
""")

w("app/models/client_recipient.py", """
from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class RecipientStatus(str, enum.Enum):
    active = "active"
    disabled = "disabled"


class ClientRecipient(Base):
    __tablename__ = "client_recipients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    funnel_form_id: Mapped[int] = mapped_column(
        ForeignKey("funnel_forms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=RecipientStatus.active.value, nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    last_sent_lead_id: Mapped[int | None] = mapped_column(nullable=True)

    funnel_form: Mapped["FunnelForm"] = relationship(
        "FunnelForm", back_populates="recipients", lazy="selectin",
        foreign_keys=[funnel_form_id]
    )

    def __repr__(self) -> str:
        return f"<ClientRecipient id={self.id} tg={self.telegram_user_id}>"
""")

w("app/models/lead.py", """
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("fb_lead_id", name="uq_leads_fb_lead_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    funnel_form_id: Mapped[int | None] = mapped_column(
        ForeignKey("funnel_forms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fb_lead_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    fb_form_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    fb_page_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivered_clients: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivered_sheet: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivery_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    funnel_form: Mapped["FunnelForm | None"] = relationship(
        "FunnelForm", back_populates="leads", lazy="selectin",
        foreign_keys=[funnel_form_id]
    )

    def __repr__(self) -> str:
        return f"<Lead id={self.id} fb_lead_id={self.fb_lead_id!r}>"
""")

w("app/models/__init__.py", """
from database import Base  # noqa: F401
from app.models.funnel_form import FunnelForm, FunnelFormStatus  # noqa: F401
from app.models.client_recipient import ClientRecipient, RecipientStatus  # noqa: F401
from app.models.lead import Lead  # noqa: F401
from app.models.preland import Preland, PrelandStatus  # noqa: F401
from app.models.preland_event import PrelandEvent, PrelandEventType  # noqa: F401

__all__ = [
    "Base",
    "FunnelForm", "FunnelFormStatus",
    "ClientRecipient", "RecipientStatus",
    "Lead",
    "Preland", "PrelandStatus",
    "PrelandEvent", "PrelandEventType",
]
""")

# ─────────────────────────────────────────────────────────────
# SERVICES
# ─────────────────────────────────────────────────────────────

w("app/services/funnel_form_service.py", """
from __future__ import annotations
import secrets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.funnel_form import FunnelForm, FunnelFormStatus


def _gen_token(prefix: str = "apex") -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def _gen_join_code() -> str:
    return secrets.token_hex(10)


async def create_funnel_form(
    session: AsyncSession,
    *,
    form_name: str,
    tag: str | None = None,
    fb_form_id: str,
    fb_page_id: str | None = None,
    google_sheet_id: str | None = None,
    google_sheet_name: str = "Leads",
    client_label: str | None = None,
    offer_name: str | None = None,
) -> FunnelForm:
    form = FunnelForm(
        form_name=form_name,
        tag=tag,
        fb_form_id=fb_form_id,
        fb_page_id=fb_page_id,
        verify_token=_gen_token(),
        join_code=_gen_join_code(),
        google_sheet_id=google_sheet_id,
        google_sheet_name=google_sheet_name or "Leads",
        client_label=client_label,
        offer_name=offer_name,
    )
    session.add(form)
    await session.flush()
    await session.refresh(form)
    return form


async def get_form_by_id(session: AsyncSession, form_id: int) -> FunnelForm | None:
    return (await session.execute(
        select(FunnelForm).where(FunnelForm.id == form_id)
    )).scalar_one_or_none()


async def get_form_by_fb_form_id(session: AsyncSession, fb_form_id: str) -> FunnelForm | None:
    return (await session.execute(
        select(FunnelForm).where(FunnelForm.fb_form_id == fb_form_id)
    )).scalar_one_or_none()


async def get_form_by_verify_token(session: AsyncSession, verify_token: str) -> FunnelForm | None:
    return (await session.execute(
        select(FunnelForm).where(FunnelForm.verify_token == verify_token)
    )).scalar_one_or_none()


async def get_form_by_join_code(
    session: AsyncSession, form_id: int, join_code: str
) -> FunnelForm | None:
    return (await session.execute(
        select(FunnelForm).where(
            FunnelForm.id == form_id,
            FunnelForm.join_code == join_code,
            FunnelForm.status == FunnelFormStatus.active.value,
        )
    )).scalar_one_or_none()


async def list_forms(session: AsyncSession) -> list[FunnelForm]:
    result = await session.execute(
        select(FunnelForm).order_by(FunnelForm.created_at.desc())
    )
    return list(result.scalars().all())


async def toggle_form_status(session: AsyncSession, form: FunnelForm) -> FunnelForm:
    if form.status == FunnelFormStatus.active.value:
        form.status = FunnelFormStatus.disabled.value
    else:
        form.status = FunnelFormStatus.active.value
    await session.flush()
    return form


async def update_apps_script_url(
    session: AsyncSession, form: FunnelForm, url: str
) -> FunnelForm:
    form.apps_script_web_app_url = url
    await session.flush()
    return form
""")

w("app/services/client_recipient_service.py", """
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
""")

w("app/services/apps_script_generator.py", """
from __future__ import annotations
from app.models.funnel_form import FunnelForm
from config import PUBLIC_BASE_URL


def generate_apps_script(form: FunnelForm) -> str:
    backend_url = PUBLIC_BASE_URL.rstrip("/")
    lead_endpoint = f"{backend_url}/api/funnel/{form.verify_token}/lead"
    health_endpoint = f"{backend_url}/health"

    return f\"\"\"// ============================================================
// AUTO-GENERATED: {form.form_name}
// Тег: {form.tag or '—'}
// FB Form ID: {form.fb_form_id}
// Verify Token: {form.verify_token}
// ============================================================
// КАК ИСПОЛЬЗОВАТЬ:
// 1. Скопируй этот код в Google Sheet → Extensions → Apps Script
// 2. Нажми Deploy → New deployment → Web App
// 3. Execute as: Me | Access: Anyone
// 4. Скопируй Web App URL
// 5. Вставь этот URL в Meta → Webhooks → Callback URL
// 6. В поле Verify Token вставь: {form.verify_token}
// 7. Подпишись на поле: leadgen
// 8. Нажми testConnection() для проверки
// ============================================================

var VERIFY_TOKEN = "{form.verify_token}";
var BACKEND_LEAD_URL = "{lead_endpoint}";
var BACKEND_HEALTH_URL = "{health_endpoint}";

// Шаг 1: Meta проверяет webhook — отвечаем на challenge
function doGet(e) {{
  if (e.parameter["hub.verify_token"] === VERIFY_TOKEN) {{
    return ContentService.createTextOutput(e.parameter["hub.challenge"]);
  }}
  return ContentService.createTextOutput("403 Forbidden");
}}

// Шаг 2: Meta присылает leadgen событие — пересылаем в backend
function doPost(e) {{
  try {{
    var resp = UrlFetchApp.fetch(BACKEND_LEAD_URL, {{
      method: "post",
      contentType: "application/json",
      payload: e.postData.contents,
      muteHttpExceptions: true
    }});
    Logger.log("Backend response: " + resp.getResponseCode() + " " + resp.getContentText());
  }} catch(err) {{
    Logger.log("Error forwarding lead: " + err);
  }}
  return ContentService.createTextOutput("ok");
}}

// Тест: проверить соединение с backend
function testConnection() {{
  try {{
    var resp = UrlFetchApp.fetch(BACKEND_HEALTH_URL, {{muteHttpExceptions: true}});
    Logger.log("Health check: " + resp.getResponseCode() + " " + resp.getContentText());
  }} catch(err) {{
    Logger.log("Connection failed: " + err);
  }}
}}

// Тест: отправить тестовый лид в backend
function testLead() {{
  var testPayload = JSON.stringify({{
    object: "page",
    entry: [{{
      id: "TEST_PAGE_ID",
      changes: [{{
        field: "leadgen",
        value: {{
          leadgen_id: "TEST_LEAD_ID_" + Date.now(),
          form_id: "{form.fb_form_id}",
          page_id: "TEST_PAGE_ID"
        }}
      }}]
    }}]
  }});
  var resp = UrlFetchApp.fetch(BACKEND_LEAD_URL, {{
    method: "post",
    contentType: "application/json",
    payload: testPayload,
    muteHttpExceptions: true
  }});
  Logger.log("Test lead response: " + resp.getResponseCode() + " " + resp.getContentText());
}}
\"\"\"
""")

w("app/services/lead_service.py", """
from __future__ import annotations
from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lead import Lead


async def create_lead(
    session: AsyncSession,
    *,
    funnel_form_id: int | None = None,
    fb_lead_id: str | None = None,
    fb_form_id: str | None = None,
    fb_page_id: str | None = None,
    full_name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    tag: str | None = None,
    raw_data_json: str | None = None,
) -> Lead:
    lead = Lead(
        funnel_form_id=funnel_form_id,
        fb_lead_id=fb_lead_id,
        fb_form_id=fb_form_id,
        fb_page_id=fb_page_id,
        full_name=full_name,
        phone=phone,
        email=email,
        tag=tag,
        raw_data_json=raw_data_json,
    )
    session.add(lead)
    await session.flush()
    await session.refresh(lead)
    return lead


async def get_lead_by_id(session: AsyncSession, lead_id: int) -> Lead | None:
    return (await session.execute(
        select(Lead).where(Lead.id == lead_id)
    )).scalar_one_or_none()


async def get_lead_by_fb_lead_id(session: AsyncSession, fb_lead_id: str) -> Lead | None:
    return (await session.execute(
        select(Lead).where(Lead.fb_lead_id == fb_lead_id)
    )).scalar_one_or_none()


async def list_leads_today(session: AsyncSession) -> list[Lead]:
    today = datetime.now().date().isoformat()
    result = await session.execute(
        select(Lead)
        .where(func.date(Lead.created_at) == today)
        .order_by(Lead.created_at.desc())
    )
    return list(result.scalars().all())


async def list_leads_by_funnel(
    session: AsyncSession, funnel_form_id: int, limit: int | None = None
) -> list[Lead]:
    q = (
        select(Lead)
        .where(Lead.funnel_form_id == funnel_form_id)
        .order_by(Lead.created_at.desc())
    )
    if limit:
        q = q.limit(limit)
    return list((await session.execute(q)).scalars().all())


async def list_leads_last_n(session: AsyncSession, n: int = 20) -> list[Lead]:
    result = await session.execute(
        select(Lead).order_by(Lead.created_at.desc()).limit(n)
    )
    return list(result.scalars().all())


async def list_leads_errors(session: AsyncSession) -> list[Lead]:
    result = await session.execute(
        select(Lead)
        .where(Lead.delivery_error.isnot(None))
        .order_by(Lead.created_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())
""")

w("app/services/delivery_service.py", """
from __future__ import annotations
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lead import Lead
from app.models.funnel_form import FunnelForm
from app.utils.formatters import format_lead_card, format_lead_notification
from config import ADMIN_IDS, GOOGLE_SERVICE_ACCOUNT_JSON

logger = logging.getLogger(__name__)
_sheets_executor = ThreadPoolExecutor(max_workers=2)


async def deliver_lead(session: AsyncSession, bot: Bot | None, lead: Lead) -> None:
    funnel: FunnelForm | None = lead.funnel_form
    errors: list[str] = []
    admin_ok = False
    clients_ok = False
    sheet_ok = False

    text_admin = format_lead_card(lead)
    text_client = format_lead_notification(lead)

    # Admin notification
    if bot and ADMIN_IDS:
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, text_admin)
                admin_ok = True
            except Exception as e:
                logger.warning("admin tg %s: %s", admin_id, e)
                errors.append(f"admin:{admin_id}:{e}")

    # Client recipients
    if bot and funnel and funnel.recipients:
        for recipient in funnel.recipients:
            if recipient.status != "active":
                continue
            try:
                await bot.send_message(recipient.telegram_user_id, text_client)
                clients_ok = True
            except Exception as e:
                logger.warning("client tg %s: %s", recipient.telegram_user_id, e)
                errors.append(f"client:{recipient.telegram_user_id}:{e}")

    # Google Sheets
    if funnel and funnel.google_sheet_id and GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            row = _build_row(lead, funnel)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                _sheets_executor,
                _append_sheet_sync,
                GOOGLE_SERVICE_ACCOUNT_JSON,
                funnel.google_sheet_id,
                funnel.google_sheet_name or "Leads",
                row,
            )
            sheet_ok = True
        except Exception as e:
            logger.error("sheets funnel %s: %s", funnel.id if funnel else "?", e)
            errors.append(f"sheet:{e}")

    lead.delivered_admin = admin_ok
    lead.delivered_clients = clients_ok
    lead.delivered_sheet = sheet_ok
    lead.delivery_error = "; ".join(str(e)[:80] for e in errors[:3]) or None
    await session.flush()


def _build_row(lead: Lead, funnel: FunnelForm | None) -> list[Any]:
    from app.utils.formatters import fmt_dt
    return [
        fmt_dt(lead.created_at),
        funnel.form_name if funnel else "",
        funnel.tag if funnel else "",
        lead.full_name or "",
        lead.phone or "",
        lead.email or "",
        lead.fb_lead_id or "",
        str(lead.id),
    ]


def _append_sheet_sync(creds_json: str, sheet_id: str, sheet_name: str, row: list) -> None:
    import gspread
    from google.oauth2.service_account import Credentials
    try:
        data = json.loads(creds_json)
    except (json.JSONDecodeError, ValueError):
        with open(creds_json) as f:
            data = json.load(f)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(data, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(sheet_name)
    except Exception:
        ws = sh.get_worksheet(0)
    ws.append_row(row, value_input_option="USER_ENTERED")
""")

# ─────────────────────────────────────────────────────────────
# WEB — new funnel webhook endpoint
# ─────────────────────────────────────────────────────────────

w("app/web/funnel_webhook.py", """
from __future__ import annotations
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.funnel_form_service import get_form_by_verify_token
from app.services.lead_service import create_lead, get_lead_by_fb_lead_id
from app.services.delivery_service import deliver_lead
from app.utils.facebook import LEADGEN_FIELD, graph_lead_url
from config import FACEBOOK_PAGE_ACCESS_TOKEN, FACEBOOK_GRAPH_VERSION
from database import get_session
import httpx

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/funnel", tags=["funnel"])


def _parse_events(payload: dict) -> list[dict]:
    events = []
    for entry in payload.get("entry", []) or []:
        page_id = str(entry.get("id") or "")
        for change in entry.get("changes", []) or []:
            if change.get("field") != LEADGEN_FIELD:
                continue
            val = change.get("value") or {}
            leadgen_id = val.get("leadgen_id") or val.get("lead_id")
            form_id = val.get("form_id")
            if leadgen_id and form_id:
                events.append({
                    "leadgen_id": str(leadgen_id),
                    "fb_form_id": str(form_id),
                    "fb_page_id": str(val.get("page_id") or page_id),
                })
    return events


async def _fetch_lead(leadgen_id: str) -> dict:
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        return {}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                graph_lead_url(FACEBOOK_GRAPH_VERSION, leadgen_id),
                params={
                    "fields": "field_data,created_time,form_id",
                    "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
                },
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.error("fetch_lead %s: %s", leadgen_id, e)
        return {}


def _normalize(raw: dict) -> dict:
    fields: dict = {}
    for item in raw.get("field_data", []) or []:
        name = str(item.get("name") or "").strip()
        values = item.get("values") or []
        val = values[0] if isinstance(values, list) and values else values
        if name:
            fields[name] = val

    def first(*names: str) -> str | None:
        for n in names:
            v = fields.get(n)
            if v:
                return str(v)
        return None

    full_name = first("full_name", "name", "your_name") or (
        " ".join(p for p in [first("first_name"), first("last_name")] if p) or None
    )
    tag = first(
        "utm_campaign", "utm_source", "utm_content", "utm_medium",
        "tag", "ref", "source", "campaign", "label",
    )
    return {
        "full_name": full_name,
        "phone": first("phone_number", "phone", "mobile"),
        "email": first("email", "email_address"),
        "tag": tag,
    }


@router.post("/{verify_token}/lead")
async def receive_lead(
    verify_token: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    form = await get_form_by_verify_token(session, verify_token)
    if not form:
        raise HTTPException(status_code=403, detail="Invalid verify token")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    events = _parse_events(payload)
    processed = 0
    for event in events:
        try:
            if await get_lead_by_fb_lead_id(session, event["leadgen_id"]):
                continue
            raw = await _fetch_lead(event["leadgen_id"])
            norm = _normalize(raw)
            tag = norm.get("tag") or form.tag
            lead = await create_lead(
                session,
                funnel_form_id=form.id,
                fb_lead_id=event["leadgen_id"],
                fb_form_id=event["fb_form_id"],
                fb_page_id=event["fb_page_id"],
                full_name=norm.get("full_name"),
                phone=norm.get("phone"),
                email=norm.get("email"),
                tag=tag,
                raw_data_json=json.dumps(raw, ensure_ascii=False),
            )
            bot = getattr(request.app.state, "bot", None)
            await deliver_lead(session, bot, lead)
            processed += 1
        except Exception as e:
            logger.error("process event %s: %s", event, e)

    return {"ok": True, "processed": processed}
""")

w("app/web/api.py", """
from aiogram import Bot
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.web.facebook_webhook import router as facebook_router
from app.web.funnel_webhook import router as funnel_router
from app.web.health import router as health_router
from app.web.preland_tracking import router as tracking_router


def create_app(bot: Bot | None = None) -> FastAPI:
    app = FastAPI(title="Apex Lead Router")
    app.state.bot = bot
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(facebook_router)
    app.include_router(funnel_router)
    app.include_router(tracking_router)
    return app
""")

# ─────────────────────────────────────────────────────────────
# FORMATTERS
# ─────────────────────────────────────────────────────────────

w("app/utils/formatters.py", """
import json
from datetime import datetime
from typing import Any
from config import PUBLIC_BASE_URL


def load_json_list(raw: str | None) -> list[Any]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def percent(part: int, total: int) -> float:
    if not total:
        return 0.0
    return round(part / total * 100, 1)


def fmt_dt(value: datetime | None) -> str:
    if not value:
        return "—"
    return value.strftime("%d.%m.%Y %H:%M")


def format_dashboard(data: dict[str, Any]) -> str:
    return (
        "\\U0001F3E0 <b>Apex Lead Router</b>\\n\\n"
        "Сегодня:\\n"
        f"\\U0001F4E5 Лидов: {data.get('leads_today', 0)}\\n"
        f"\\u2705 Доставлено: {data.get('delivered_today', 0)}\\n"
        f"\\u26A0\\uFE0F Ошибок: {data.get('delivery_errors_today', 0)}\\n\\n"
        "Prelands:\\n"
        f"\\U0001F441 Заходов: {data.get('preland_visits_today', 0)}\\n"
        f"\\U0001F446 Кликов: {data.get('preland_clicks_today', 0)}\\n"
        f"\\U0001F4C8 CTR: {data.get('preland_ctr_today', 0)}%\\n\\n"
        "Что открыть?"
    )


def format_lead_notification(lead: Any) -> str:
    \"\"\"Чистое уведомление для получателя (клиента).\"\"\"
    _d = "—"
    try:
        tag = lead.tag or (lead.funnel_form.tag if lead.funnel_form else None) or _d
        form_name = lead.funnel_form.form_name if lead.funnel_form else _d
    except Exception:
        tag = _d
        form_name = _d

    lines = [
        "\\U0001F525 <b>Новый лид!</b>",
        "",
        f"\\U0001F3F7 <b>Тег:</b> {tag}",
        f"\\U0001F4CB <b>Форма:</b> {form_name}",
        "",
        f"\\U0001F464 <b>Имя:</b> {lead.full_name or _d}",
        f"\\U0001F4DE <b>Телефон:</b> {lead.phone or _d}",
    ]
    if lead.email:
        lines.append(f"\\U0001F4E7 <b>Email:</b> {lead.email}")
    lines += ["", f"\\U0001F552 <b>Дата:</b> {fmt_dt(lead.created_at)}"]
    return "\\n".join(lines)


def format_lead_card(lead: Any) -> str:
    \"\"\"Полная карточка лида для администратора.\"\"\"
    _d = "—"
    try:
        form_name = lead.funnel_form.form_name if lead.funnel_form else _d
        tag = lead.tag or (lead.funnel_form.tag if lead.funnel_form else None) or _d
    except Exception:
        form_name = _d
        tag = _d

    adm = "\\u2705" if lead.delivered_admin else "\\u274C"
    cli = "\\u2705" if lead.delivered_clients else "\\u2014"
    sh = "\\u2705" if lead.delivered_sheet else "\\u2014"

    text = (
        f"\\U0001F4E5 <b>Лид #{lead.id}</b>\\n\\n"
        f"Форма: {form_name}\\n"
        f"Тег: {tag}\\n"
        f"Дата: {fmt_dt(lead.created_at)}\\n\\n"
        f"Имя: {lead.full_name or _d}\\n"
        f"Телефон: {lead.phone or _d}\\n"
        f"Email: {lead.email or _d}\\n\\n"
        f"Доставка:\\n"
        f"Админ: {adm}  Клиенты: {cli}  Sheet: {sh}\\n"
    )
    if lead.delivery_error:
        text += f"\\n\\u26A0\\uFE0F {lead.delivery_error[:200]}"
    return text


def format_funnel_card(form: Any, leads_total: int, leads_today: int, recipients_count: int) -> str:
    _d = "—"
    sheet_status = "✅ подключён" if form.google_sheet_id else "❌ не подключён"
    status_icon = "🟢" if form.status == "active" else "🔴"
    return (
        f"{status_icon} <b>{form.form_name}</b>\\n\\n"
        f"Тег: {form.tag or _d}\\n"
        f"FB Form ID: <code>{form.fb_form_id}</code>\\n\\n"
        f"Получателей: {recipients_count}\\n"
        f"Лидов всего: {leads_total}\\n"
        f"Лидов сегодня: {leads_today}\\n\\n"
        f"Google Sheet: {sheet_status}"
    )
""")

# ─────────────────────────────────────────────────────────────
# BOT KEYBOARDS
# ─────────────────────────────────────────────────────────────

w("app/bot/keyboards/main_kb.py", """
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать форму", callback_data="funnel:create")],
        [
            InlineKeyboardButton(text="📋 Мои формы", callback_data="funnel:list"),
            InlineKeyboardButton(text="📥 Лиды", callback_data="leads:menu"),
        ],
        [
            InlineKeyboardButton(text="🌐 Prelands", callback_data="prelands:menu"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats:menu"),
        ],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings:menu")],
    ])
""")

w("app/bot/keyboards/funnel_kb.py", """
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def funnel_list_kb(forms: list) -> InlineKeyboardMarkup:
    buttons = []
    for f in forms:
        icon = "🟢" if f.status == "active" else "🔴"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {f.form_name}",
            callback_data=f"funnel:card:{f.id}",
        )])
    buttons.append([InlineKeyboardButton(text="➕ Создать форму", callback_data="funnel:create")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def funnel_card_kb(form_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_text = "⏸ Выключить" if is_active else "▶️ Включить"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Код Apps Script", callback_data=f"funnel:code:{form_id}")],
        [InlineKeyboardButton(text="👥 Подключить клиента", callback_data=f"funnel:joinlink:{form_id}")],
        [
            InlineKeyboardButton(text="📥 Лиды формы", callback_data=f"funnel:leads:{form_id}"),
            InlineKeyboardButton(text="👤 Получатели", callback_data=f"funnel:recipients:{form_id}"),
        ],
        [InlineKeyboardButton(text=toggle_text, callback_data=f"funnel:toggle:{form_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="funnel:list")],
    ])


def funnel_join_notify_kb(form_id: int, recipient_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📤 Все старые", callback_data=f"funnel:sendold:{recipient_id}:all"),
            InlineKeyboardButton(text="📤 Последние 20", callback_data=f"funnel:sendold:{recipient_id}:last20"),
        ],
        [InlineKeyboardButton(text="⏭ Только новые", callback_data=f"funnel:sendold:{recipient_id}:skip")],
        [InlineKeyboardButton(text="📥 Лиды формы", callback_data=f"funnel:leads:{form_id}")],
    ])


def funnel_sendold_options_kb(recipient_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📤 Все", callback_data=f"funnel:sendold:{recipient_id}:all"),
            InlineKeyboardButton(text="📤 Последние 20", callback_data=f"funnel:sendold:{recipient_id}:last20"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="funnel:list")],
    ])


def recipients_list_kb(recipients: list, form_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for r in recipients:
        name = r.first_name or r.telegram_username or str(r.telegram_user_id)
        buttons.append([
            InlineKeyboardButton(text=f"👤 {name}", callback_data=f"funnel:sendold:{r.id}:choose"),
            InlineKeyboardButton(text="❌", callback_data=f"funnel:delrecip:{r.id}:{form_id}"),
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"funnel:card:{form_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def sheet_choice_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, подключить таблицу", callback_data="wizard:sheet:yes")],
        [InlineKeyboardButton(text="⏭ Позже", callback_data="wizard:sheet:skip")],
    ])


def skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="wizard:skip")],
    ])
""")

# ─────────────────────────────────────────────────────────────
# BOT HANDLERS
# ─────────────────────────────────────────────────────────────

w("app/bot/handlers/funnel.py", """
from __future__ import annotations
import asyncio
from datetime import datetime
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.funnel_kb import (
    funnel_card_kb, funnel_join_notify_kb, funnel_list_kb, funnel_sendold_options_kb,
    recipients_list_kb, sheet_choice_kb, skip_kb,
)
from app.bot.keyboards.leads_kb import leads_list_kb
from app.services.apps_script_generator import generate_apps_script
from app.services.client_recipient_service import (
    get_or_create_recipient, list_recipients, remove_recipient, send_leads_to_recipient,
)
from app.services.funnel_form_service import (
    create_funnel_form, get_form_by_id, list_forms, toggle_form_status,
)
from app.services.lead_service import list_leads_by_funnel
from app.utils.formatters import fmt_dt, format_funnel_card
from config import ADMIN_IDS, BOT_USERNAME

router = Router(name="funnel")


# ── FSM STATES ──────────────────────────────────────────────
class FunnelFSM(StatesGroup):
    form_name = State()
    tag = State()
    fb_form_id = State()
    fb_page_id = State()
    sheet_choice = State()
    sheet_id = State()
    sheet_name = State()


# ── LIST & CREATE ────────────────────────────────────────────

@router.callback_query(lambda c: c.data == "funnel:list")
async def funnel_list(callback: CallbackQuery, session: AsyncSession) -> None:
    forms = await list_forms(session)
    text = f"📋 <b>Мои лид-формы</b>\\n\\nВсего: {len(forms)}"
    await callback.message.edit_text(text, reply_markup=funnel_list_kb(forms))
    await callback.answer()


@router.callback_query(lambda c: c.data == "funnel:create")
async def funnel_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(FunnelFSM.form_name)
    await callback.message.edit_text(
        "➕ <b>Создание лид-формы</b>\\n\\n"
        "<b>Шаг 1/4.</b> Как называется лид-форма?\\n\\n"
        "<i>Пример: SkyX PL 18-30</i>"
    )
    await callback.answer()


@router.message(FunnelFSM.form_name)
async def wizard_form_name(message: Message, state: FSMContext) -> None:
    await state.update_data(form_name=message.text.strip())
    await state.set_state(FunnelFSM.tag)
    await message.answer(
        "<b>Шаг 2/4.</b> Тег / оффер для сообщений?\\n\\n"
        "<i>Пример: SkyX / PL / 18-30 / preland</i>\\n"
        "<i>Этот текст будет в каждом уведомлении о лиде.</i>"
    )


@router.message(FunnelFSM.tag)
async def wizard_tag(message: Message, state: FSMContext) -> None:
    await state.update_data(tag=message.text.strip())
    await state.set_state(FunnelFSM.fb_form_id)
    await message.answer(
        "<b>Шаг 3/4.</b> Facebook Form ID?\\n\\n"
        "<i>Найти: Meta Business Suite → Лид-формы → выбрать форму → ID в URL</i>\\n"
        "<i>Пример: 941541071981</i>"
    )


@router.message(FunnelFSM.fb_form_id)
async def wizard_fb_form_id(message: Message, state: FSMContext) -> None:
    await state.update_data(fb_form_id=message.text.strip())
    await state.set_state(FunnelFSM.fb_page_id)
    await message.answer(
        "<b>Шаг 4/4.</b> Facebook Page ID? (необязательно)\\n\\n"
        "<i>Можно пропустить — нажми кнопку ниже.</i>",
        reply_markup=skip_kb(),
    )


@router.callback_query(lambda c: c.data == "wizard:skip")
async def wizard_skip_page_id(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(fb_page_id=None)
    await state.set_state(FunnelFSM.sheet_choice)
    await callback.message.edit_text(
        "Подключить <b>Google Sheet</b> для автозаписи лидов?",
        reply_markup=sheet_choice_kb(),
    )
    await callback.answer()


@router.message(FunnelFSM.fb_page_id)
async def wizard_fb_page_id(message: Message, state: FSMContext) -> None:
    await state.update_data(fb_page_id=message.text.strip())
    await state.set_state(FunnelFSM.sheet_choice)
    await message.answer(
        "Подключить <b>Google Sheet</b> для автозаписи лидов?",
        reply_markup=sheet_choice_kb(),
    )


@router.callback_query(lambda c: c.data == "wizard:sheet:skip")
async def wizard_sheet_skip(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.update_data(google_sheet_id=None, google_sheet_name="Leads")
    await _finish_wizard(callback, state, session)


@router.callback_query(lambda c: c.data == "wizard:sheet:yes")
async def wizard_sheet_yes(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FunnelFSM.sheet_id)
    await callback.message.edit_text(
        "📊 Введи <b>Google Sheet ID</b>:\\n\\n"
        "<i>Найти: открой таблицу → в URL между /d/ и /edit</i>\\n"
        "<i>Пример: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms</i>"
    )
    await callback.answer()


@router.message(FunnelFSM.sheet_id)
async def wizard_sheet_id(message: Message, state: FSMContext) -> None:
    await state.update_data(google_sheet_id=message.text.strip())
    await state.set_state(FunnelFSM.sheet_name)
    await message.answer(
        "Название листа? (по умолчанию: Leads)\\n\\n"
        "<i>Нажми /skip или введи название</i>",
        reply_markup=skip_kb(),
    )


@router.message(FunnelFSM.sheet_name)
async def wizard_sheet_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    text = message.text.strip()
    if text.lower() in ("/skip", "пропустить", "skip"):
        text = "Leads"
    await state.update_data(google_sheet_name=text)
    # fake callback-like finish
    data = await state.get_data()
    await state.clear()
    form = await create_funnel_form(
        session,
        form_name=data["form_name"],
        tag=data.get("tag"),
        fb_form_id=data["fb_form_id"],
        fb_page_id=data.get("fb_page_id"),
        google_sheet_id=data.get("google_sheet_id"),
        google_sheet_name=data.get("google_sheet_name", "Leads"),
    )
    await message.answer(_form_created_text(form), reply_markup=funnel_card_kb(form.id, True))


async def _finish_wizard(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    await state.clear()
    form = await create_funnel_form(
        session,
        form_name=data["form_name"],
        tag=data.get("tag"),
        fb_form_id=data["fb_form_id"],
        fb_page_id=data.get("fb_page_id"),
        google_sheet_id=data.get("google_sheet_id"),
        google_sheet_name=data.get("google_sheet_name", "Leads"),
    )
    await callback.message.edit_text(_form_created_text(form), reply_markup=funnel_card_kb(form.id, True))
    await callback.answer()


def _form_created_text(form) -> str:
    sheet_status = f"✅ {form.google_sheet_id}" if form.google_sheet_id else "❌ не подключён"
    return (
        f"✅ <b>Лид-форма создана!</b>\\n\\n"
        f"Форма: <b>{form.form_name}</b>\\n"
        f"Тег: {form.tag or '—'}\\n"
        f"FB Form ID: <code>{form.fb_form_id}</code>\\n"
        f"Verify Token: <code>{form.verify_token}</code>\\n"
        f"Google Sheet: {sheet_status}\\n\\n"
        f"<b>Что дальше:</b>\\n"
        f"1. Нажми <b>📋 Код Apps Script</b> — скопируй код\\n"
        f"2. Вставь в Google Sheet → Extensions → Apps Script\\n"
        f"3. Deploy → New deployment → Web App (Anyone)\\n"
        f"4. Полученный URL → Meta → Webhooks → Callback URL\\n"
        f"5. Verify Token: <code>{form.verify_token}</code>\\n"
        f"6. Подпишись на поле <b>leadgen</b>\\n"
        f"7. Отправь тестовый лид"
    )


# ── FORM CARD ────────────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("funnel:card:"))
async def funnel_card(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[2])
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена.", show_alert=True)
        return
    today = datetime.now().date().isoformat()
    all_leads = await list_leads_by_funnel(session, form_id)
    today_leads = [l for l in all_leads if l.created_at.date().isoformat() == today]
    recipients = await list_recipients(session, form_id)
    text = format_funnel_card(form, len(all_leads), len(today_leads), len(recipients))
    await callback.message.edit_text(text, reply_markup=funnel_card_kb(form_id, form.status == "active"))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:toggle:"))
async def funnel_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[2])
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена.", show_alert=True)
        return
    form = await toggle_form_status(session, form)
    status = "активна" if form.status == "active" else "выключена"
    await callback.answer(f"Форма {status}.", show_alert=True)
    # refresh card
    today = datetime.now().date().isoformat()
    all_leads = await list_leads_by_funnel(session, form_id)
    today_leads = [l for l in all_leads if l.created_at.date().isoformat() == today]
    recipients = await list_recipients(session, form_id)
    text = format_funnel_card(form, len(all_leads), len(today_leads), len(recipients))
    await callback.message.edit_text(text, reply_markup=funnel_card_kb(form_id, form.status == "active"))


# ── APPS SCRIPT CODE ─────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("funnel:code:"))
async def funnel_code(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[2])
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена.", show_alert=True)
        return
    code = generate_apps_script(form)
    # Send as a separate message (code too long for edit)
    await callback.message.answer(
        f"📋 <b>Код Apps Script для: {form.form_name}</b>\\n\\n"
        f"<code>{code}</code>"
    )
    await callback.answer()


# ── JOIN LINK ────────────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("funnel:joinlink:"))
async def funnel_joinlink(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[2])
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена.", show_alert=True)
        return
    link = f"https://t.me/{BOT_USERNAME}?start=join_{form.id}_{form.join_code}"
    await callback.message.edit_text(
        f"👥 <b>Подключение клиента к форме</b>\\n\\n"
        f"Форма: <b>{form.form_name}</b>\\n"
        f"Тег: {form.tag or '—'}\\n\\n"
        f"Отправь клиенту эту ссылку:\\n"
        f"<code>{link}</code>\\n\\n"
        f"Когда клиент нажмёт — он автоматически добавится в получатели.\\n"
        f"Ты получишь уведомление и сможешь отправить ему старые заявки.",
        reply_markup=funnel_card_kb(form_id, form.status == "active"),
    )
    await callback.answer()


# ── RECIPIENTS LIST ──────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("funnel:recipients:"))
async def funnel_recipients(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[2])
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена.", show_alert=True)
        return
    recipients = await list_recipients(session, form_id)
    text = (
        f"👥 <b>Получатели: {form.form_name}</b>\\n\\n"
        f"Активных: {len(recipients)}"
    )
    await callback.message.edit_text(text, reply_markup=recipients_list_kb(recipients, form_id))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:delrecip:"))
async def funnel_del_recipient(callback: CallbackQuery, session: AsyncSession) -> None:
    parts = callback.data.split(":")
    recipient_id = int(parts[2])
    form_id = int(parts[3])
    await remove_recipient(session, recipient_id)
    recipients = await list_recipients(session, form_id)
    form = await get_form_by_id(session, form_id)
    await callback.message.edit_text(
        f"👥 <b>Получатели: {form.form_name if form else '—'}</b>\\n\\nАктивных: {len(recipients)}",
        reply_markup=recipients_list_kb(recipients, form_id),
    )
    await callback.answer("Получатель удалён.")


# ── LEADS OF FORM ────────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("funnel:leads:"))
async def funnel_leads(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[2])
    leads = await list_leads_by_funnel(session, form_id, limit=30)
    if not leads:
        await callback.answer("Лидов нет.", show_alert=True)
        return
    await callback.message.edit_text(
        f"📥 Лиды формы (последние {len(leads)}):",
        reply_markup=leads_list_kb(leads, back_cb=f"funnel:card:{form_id}"),
    )
    await callback.answer()


# ── SEND OLD LEADS ───────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("funnel:sendold:"))
async def funnel_sendold(callback: CallbackQuery, session: AsyncSession) -> None:
    parts = callback.data.split(":")
    recipient_id = int(parts[2])
    mode = parts[3] if len(parts) > 3 else "choose"

    from app.models.client_recipient import ClientRecipient
    from sqlalchemy import select as sa_select
    recipient = (await session.execute(
        sa_select(ClientRecipient).where(ClientRecipient.id == recipient_id)
    )).scalar_one_or_none()
    if not recipient:
        await callback.answer("Получатель не найден.", show_alert=True)
        return

    if mode == "choose":
        await callback.message.edit_text(
            "Сколько старых лидов отправить?",
            reply_markup=funnel_sendold_options_kb(recipient_id),
        )
        await callback.answer()
        return

    if mode == "skip":
        await callback.answer("Ок, только новые заявки.", show_alert=True)
        return

    form_id = recipient.funnel_form_id
    limit = None if mode == "all" else 20
    leads = await list_leads_by_funnel(session, form_id, limit=limit)
    if not leads:
        await callback.answer("Лидов нет.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(
        f"⏳ Отправляю {len(leads)} лидов получателю...\\n\\nПожалуйста, подожди."
    )

    bot = callback.bot
    sent, errors = await send_leads_to_recipient(bot, recipient, leads)

    form = await get_form_by_id(session, form_id)
    name = recipient.first_name or recipient.telegram_username or str(recipient.telegram_user_id)
    await callback.message.edit_text(
        f"✅ <b>Отправка завершена</b>\\n\\n"
        f"Получатель: {name}\\n"
        f"Форма: {form.form_name if form else '—'}\\n\\n"
        f"Отправлено: {sent}\\n"
        f"Ошибок: {errors}",
        reply_markup=funnel_card_kb(form_id, form.status == "active" if form else True),
    )
""")

w("app/bot/handlers/menu.py", """
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.main_kb import main_menu_kb
from app.bot.keyboards.funnel_kb import funnel_join_notify_kb
from app.services.funnel_form_service import get_form_by_join_code
from app.services.client_recipient_service import get_or_create_recipient, list_recipients
from app.services.stats_service import dashboard_today
from app.utils.formatters import format_dashboard
from config import ADMIN_IDS

router = Router(name="menu")


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession) -> None:
    args = message.text.split(maxsplit=1)[1] if message.text and " " in message.text else ""

    # /start join_{form_id}_{join_code}
    if args.startswith("join_"):
        parts = args[5:].split("_", 1)
        if len(parts) == 2:
            try:
                form_id = int(parts[0])
                join_code = parts[1]
            except ValueError:
                form_id = None
                join_code = None
            if form_id and join_code:
                form = await get_form_by_join_code(session, form_id, join_code)
                if form:
                    user = message.from_user
                    recipient, is_new = await get_or_create_recipient(
                        session,
                        funnel_form_id=form.id,
                        telegram_user_id=user.id,
                        telegram_username=user.username,
                        first_name=user.first_name,
                    )
                    if is_new:
                        await message.answer(
                            f"✅ <b>Вы подключены!</b>\\n\\n"
                            f"Теперь вы будете получать заявки по форме:\\n"
                            f"<b>{form.form_name}</b>\\n\\n"
                            f"Тег: {form.tag or '—'}"
                        )
                        # Notify admins
                        uname = f"@{user.username}" if user.username else user.full_name
                        recipients = await list_recipients(session, form.id)
                        for admin_id in ADMIN_IDS:
                            try:
                                await message.bot.send_message(
                                    admin_id,
                                    f"👥 <b>Новый получатель подключён</b>\\n\\n"
                                    f"Форма: <b>{form.form_name}</b>\\n"
                                    f"Пользователь: {uname}\\n"
                                    f"Telegram ID: <code>{user.id}</code>\\n\\n"
                                    f"Отправить ему старые заявки?",
                                    reply_markup=funnel_join_notify_kb(form.id, recipient.id),
                                )
                            except Exception:
                                pass
                    else:
                        await message.answer(
                            f"ℹ️ Вы уже подключены к форме <b>{form.form_name}</b>"
                        )
                    return
                else:
                    await message.answer("❌ Ссылка недействительна или форма выключена.")
                    return

    data = await dashboard_today(session)
    await message.answer(format_dashboard(data), reply_markup=main_menu_kb())


@router.callback_query(lambda c: c.data == "main:menu")
async def main_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    data = await dashboard_today(session)
    await callback.message.edit_text(format_dashboard(data), reply_markup=main_menu_kb())
    await callback.answer()
""")

w("app/bot/handlers/__init__.py", """
from app.bot.handlers.menu import router as menu_router
from app.bot.handlers.funnel import router as funnel_router
from app.bot.handlers.leads import router as leads_router
from app.bot.handlers.prelands import router as prelands_router
from app.bot.handlers.stats import router as stats_router
from app.bot.handlers.settings import router as settings_router

routers = [
    menu_router,
    funnel_router,
    leads_router,
    prelands_router,
    stats_router,
    settings_router,
]

__all__ = ["routers"]
""")

# ─────────────────────────────────────────────────────────────
# MIGRATION 008
# ─────────────────────────────────────────────────────────────

w("alembic/versions/008_funnel_form.py", """
\"\"\"FunnelForm + ClientRecipient - new architecture

Revision ID: 008
Revises: 007
Create Date: 2026-05-08
\"\"\"
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # 1. funnel_forms
    if "funnel_forms" not in tables:
        op.create_table(
            "funnel_forms",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("form_name", sa.String(255), nullable=False),
            sa.Column("client_label", sa.String(255), nullable=True),
            sa.Column("offer_name", sa.String(255), nullable=True),
            sa.Column("tag", sa.String(255), nullable=True),
            sa.Column("fb_form_id", sa.String(100), nullable=False, unique=True),
            sa.Column("fb_page_id", sa.String(100), nullable=True),
            sa.Column("verify_token", sa.String(100), nullable=False, unique=True),
            sa.Column("join_code", sa.String(100), nullable=False, unique=True),
            sa.Column("google_sheet_id", sa.String(200), nullable=True),
            sa.Column("google_sheet_name", sa.String(200), nullable=False, server_default="Leads"),
            sa.Column("apps_script_web_app_url", sa.String(500), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_funnel_forms_fb_form_id", "funnel_forms", ["fb_form_id"])
        op.create_index("ix_funnel_forms_verify_token", "funnel_forms", ["verify_token"])
        op.create_index("ix_funnel_forms_status", "funnel_forms", ["status"])

    # 2. client_recipients
    if "client_recipients" not in tables:
        op.create_table(
            "client_recipients",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("funnel_form_id", sa.Integer, sa.ForeignKey("funnel_forms.id", ondelete="CASCADE"), nullable=False),
            sa.Column("telegram_user_id", sa.BigInteger, nullable=False),
            sa.Column("telegram_username", sa.String(255), nullable=True),
            sa.Column("first_name", sa.String(255), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("joined_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.Column("last_sent_lead_id", sa.Integer, nullable=True),
        )
        op.create_index("ix_client_recipients_funnel_form_id", "client_recipients", ["funnel_form_id"])
        op.create_index("ix_client_recipients_telegram_user_id", "client_recipients", ["telegram_user_id"])

    # 3. Update leads table — add new columns (old ones stay, SQLite-safe)
    if "leads" in tables:
        existing_cols = {c["name"] for c in inspector.get_columns("leads")}
        new_cols = {
            "funnel_form_id": sa.Column("funnel_form_id", sa.Integer, nullable=True),
            "fb_form_id": sa.Column("fb_form_id", sa.String(100), nullable=True),
            "fb_page_id": sa.Column("fb_page_id", sa.String(100), nullable=True),
            "delivered_admin": sa.Column("delivered_admin", sa.Boolean, nullable=False, server_default="0"),
            "delivered_clients": sa.Column("delivered_clients", sa.Boolean, nullable=False, server_default="0"),
        }
        for col_name, col_def in new_cols.items():
            if col_name not in existing_cols:
                op.add_column("leads", col_def)
        # Create index on funnel_form_id if not exists
        try:
            op.create_index("ix_leads_funnel_form_id", "leads", ["funnel_form_id"])
        except Exception:
            pass
        try:
            op.create_index("ix_leads_fb_form_id", "leads", ["fb_form_id"])
        except Exception:
            pass


def downgrade() -> None:
    op.drop_table("client_recipients")
    op.drop_table("funnel_forms")
""")

print("\\n✅ All files written successfully!")
print("\\nNext steps:")
print("  python -m alembic upgrade head")
print("  python -m py_compile app/models/funnel_form.py app/models/client_recipient.py app/models/lead.py")
print("  python -m py_compile app/services/funnel_form_service.py app/services/client_recipient_service.py")
print("  python -m py_compile app/services/delivery_service.py app/services/apps_script_generator.py")
print("  python -m py_compile app/web/funnel_webhook.py app/web/api.py")
print("  python -m py_compile app/bot/handlers/funnel.py app/bot/handlers/menu.py")
