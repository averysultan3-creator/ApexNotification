import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.referral_source import ReferralSource, ReferralStatus, SourceType
from config import BOT_USERNAME


def _generate_code() -> str:
    return uuid.uuid4().hex[:8]


def build_start_link(form_id: int, ref_code: str) -> str:
    return f"https://t.me/{BOT_USERNAME}?start=lf_{form_id}_ref_{ref_code}"


async def _unique_code(session: AsyncSession) -> str:
    while True:
        code = _generate_code()
        result = await session.execute(
            select(ReferralSource).where(ReferralSource.code == code)
        )
        if result.scalar_one_or_none() is None:
            return code


async def get_refs_by_form(
    session: AsyncSession, form_id: int, active_only: bool = False
) -> List[ReferralSource]:
    q = select(ReferralSource).where(ReferralSource.form_id == form_id)
    if active_only:
        q = q.where(ReferralSource.status == ReferralStatus.active.value)
    result = await session.execute(q.order_by(ReferralSource.name))
    return list(result.scalars().all())


async def get_all_refs(
    session: AsyncSession, active_only: bool = False
) -> List[ReferralSource]:
    """Return every referral source, optionally filtered to active only."""
    q = select(ReferralSource)
    if active_only:
        q = q.where(ReferralSource.status == ReferralStatus.active.value)
    result = await session.execute(q.order_by(ReferralSource.name))
    return list(result.scalars().all())


async def get_ref_by_id(
    session: AsyncSession, ref_id: int
) -> Optional[ReferralSource]:
    result = await session.execute(
        select(ReferralSource).where(ReferralSource.id == ref_id)
    )
    return result.scalar_one_or_none()


async def get_ref_by_code(
    session: AsyncSession, code: str
) -> Optional[ReferralSource]:
    result = await session.execute(
        select(ReferralSource).where(ReferralSource.code == code)
    )
    return result.scalar_one_or_none()


async def create_referral(
    session: AsyncSession,
    form_id: int,
    name: str,
    source_type: str = SourceType.other.value,
    notes: Optional[str] = None,
) -> ReferralSource:
    code = await _unique_code(session)
    ref = ReferralSource(
        form_id=form_id,
        name=name,
        code=code,
        source_type=source_type,
        notes=notes,
        status=ReferralStatus.active.value,
    )
    session.add(ref)
    await session.flush()
    await session.refresh(ref)
    return ref


async def update_ref_field(
    session: AsyncSession, ref_id: int, field: str, value: str
) -> Optional[ReferralSource]:
    ref = await get_ref_by_id(session, ref_id)
    if not ref:
        return None
    allowed = {"name", "source_type", "notes"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' is not editable.")
    setattr(ref, field, value if value else None)
    await session.flush()
    await session.refresh(ref)
    return ref


async def toggle_ref_status(session: AsyncSession, ref_id: int) -> Optional[ReferralSource]:
    ref = await get_ref_by_id(session, ref_id)
    if not ref:
        return None
    ref.status = (
        ReferralStatus.inactive.value
        if ref.status == ReferralStatus.active.value
        else ReferralStatus.active.value
    )
    await session.flush()
    await session.refresh(ref)
    return ref


async def delete_ref(session: AsyncSession, ref_id: int) -> bool:
    ref = await get_ref_by_id(session, ref_id)
    if not ref:
        return False
    await session.delete(ref)
    await session.flush()
    return True
