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
