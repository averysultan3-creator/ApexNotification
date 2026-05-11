from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.client_kb import (
    client_archive_kb,
    client_cabinet_kb,
    client_funnel_kb,
    client_no_funnels_kb,
    client_stats_back_kb,
)
from app.models.client_recipient import ClientRecipient, RecipientStatus
from app.models.funnel_form import FunnelForm
from app.models.lead import Lead
from app.services.stats_service import (
    client_stats,
    client_stats_by_day,
    client_stats_today_by_hour,
)
from app.utils.formatters import fmt_dt

logger = logging.getLogger(__name__)

router = Router(name="client")
PAGE_SIZE = 10


async def _get_client_funnel_ids(session: AsyncSession, user_id: int) -> list[int]:
    rows = (await session.execute(
        select(ClientRecipient.funnel_form_id).where(
            ClientRecipient.telegram_user_id == user_id,
            ClientRecipient.status == RecipientStatus.active.value,
        )
    )).scalars().all()
    return list(rows)


async def _get_funnel(session: AsyncSession, form_id: int) -> FunnelForm | None:
    return (await session.execute(
        select(FunnelForm).where(FunnelForm.id == form_id)
    )).scalar_one_or_none()


async def _verify_access(session: AsyncSession, user_id: int, form_id: int) -> bool:
    exists = (await session.execute(
        select(ClientRecipient.id).where(
            ClientRecipient.telegram_user_id == user_id,
            ClientRecipient.funnel_form_id == form_id,
            ClientRecipient.status == RecipientStatus.active.value,
        )
    )).scalar_one_or_none()
    return exists is not None


async def show_cabinet(
    event: Message | CallbackQuery,
    session: AsyncSession,
    edit: bool = False,
) -> None:
    user_id = event.from_user.id
    funnel_ids = await _get_client_funnel_ids(session, user_id)

    if not funnel_ids:
        text = (
            "<b>Рекламный кабинет</b>\n\n"
            "Вы пока не подключены ни к одной воронке.\n"
            "Используйте ссылку от вашего администратора."
        )
        keyboard = client_no_funnels_kb()
        if isinstance(event, Message):
            await event.answer(text, reply_markup=keyboard)
        else:
            await event.message.edit_text(text, reply_markup=keyboard)
        return

    funnels = (await session.execute(
        select(FunnelForm).where(FunnelForm.id.in_(funnel_ids))
    )).scalars().all()

    text = "<b>Рекламный кабинет</b>\n\nВаши воронки:"
    keyboard = client_cabinet_kb(funnels)

    if isinstance(event, Message):
        await event.answer(text, reply_markup=keyboard)
    else:
        try:
            await event.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await event.message.answer(text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "cl:cabinet")
async def on_cabinet(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    await show_cabinet(callback, session)


@router.callback_query(lambda c: c.data and c.data.startswith("cl:funnel:"))
async def on_funnel(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    form_id = int(callback.data.split(":")[-1])

    if not await _verify_access(session, callback.from_user.id, form_id):
        await callback.answer("Нет доступа к этой воронке.", show_alert=True)
        return

    form = await _get_funnel(session, form_id)
    if not form:
        await callback.answer("Воронка не найдена.", show_alert=True)
        return

    stats = await client_stats(session, form_id, callback.from_user.id)
    last = fmt_dt(stats["last_lead_at"])
    text = (
        f"<b>{form.form_name}</b>\n\n"
        f"Сегодня: <b>{stats['leads_today']}</b> лидов\n"
        f"7 дней: <b>{stats['leads_7d']}</b>\n"
        f"30 дней: <b>{stats['leads_30d']}</b>\n\n"
        f"Последний лид: {last}"
    )
    await callback.message.edit_text(text, reply_markup=client_funnel_kb(form_id))


@router.callback_query(lambda c: c.data and c.data.startswith("cl:stats_today:"))
async def on_stats_today(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    form_id = int(callback.data.split(":")[-1])

    if not await _verify_access(session, callback.from_user.id, form_id):
        await callback.answer("ет доступа к этой воронке.", show_alert=True)
        return

    by_hour = await client_stats_today_by_hour(session, form_id)
    if not by_hour:
        body = "Сегодня лидов нет."
    else:
        lines = ["<b>Сегодня по часам:</b>\n"]
        for row in by_hour:
            bar = "#" * min(row["count"], 20)
            lines.append(f"{row['hour']:02d}:00  {bar} {row['count']}")
        body = "\n".join(lines)

    await callback.message.edit_text(body, reply_markup=client_stats_back_kb(form_id))


@router.callback_query(lambda c: c.data and c.data.startswith("cl:stats_7d:"))
async def on_stats_7d(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    form_id = int(callback.data.split(":")[-1])

    if not await _verify_access(session, callback.from_user.id, form_id):
        await callback.answer("ет доступа к этой воронке.", show_alert=True)
        return

    by_day = await client_stats_by_day(session, form_id, days=7)
    lines = ["<b>Последние 7 дней:</b>\n"]
    for row in by_day:
        day = row["date"].strftime("%d.%m")
        bar = "#" * min(row["count"], 20)
        lines.append(f"{day}  {bar} {row['count']}")
    await callback.message.edit_text("\n".join(lines), reply_markup=client_stats_back_kb(form_id))


@router.callback_query(lambda c: c.data and c.data.startswith("cl:stats_30d:"))
async def on_stats_30d(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    form_id = int(callback.data.split(":")[-1])

    if not await _verify_access(session, callback.from_user.id, form_id):
        await callback.answer("ет доступа к этой воронке.", show_alert=True)
        return

    by_day = await client_stats_by_day(session, form_id, days=30)
    total = sum(row["count"] for row in by_day)
    avg = round(total / 30, 1)
    lines = [
        "<b>Последние 30 дней:</b>\n",
        f"Всего: {total} лидов",
        f"В среднем: {avg}/день",
        "",
    ]
    for row in by_day[:10]:
        day = row["date"].strftime("%d.%m")
        bar = "#" * min(row["count"], 20)
        lines.append(f"{day}  {bar} {row['count']}")
    if len(by_day) > 10:
        lines.append("...")
    await callback.message.edit_text("\n".join(lines), reply_markup=client_stats_back_kb(form_id))


@router.callback_query(lambda c: c.data and c.data.startswith("cl:archive:"))
async def on_archive(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    parts = callback.data.split(":")
    form_id = int(parts[2])
    page = int(parts[3])

    if not await _verify_access(session, callback.from_user.id, form_id):
        await callback.answer("ет доступа к этой воронке.", show_alert=True)
        return

    offset = page * PAGE_SIZE
    leads = (await session.execute(
        select(Lead).where(Lead.funnel_form_id == form_id)
        .order_by(Lead.created_at.desc())
        .offset(offset)
        .limit(PAGE_SIZE + 1)
    )).scalars().all()

    has_next = len(leads) > PAGE_SIZE
    leads = leads[:PAGE_SIZE]
    has_prev = page > 0

    if not leads:
        await callback.message.edit_text(
            "Лидов пока нет.",
            reply_markup=client_archive_kb(form_id, page, has_prev=False, has_next=False),
        )
        return

    lines = [f"<b>Архив лидов</b> (страница {page + 1})\n"]
    for lead in leads:
        date_str = fmt_dt(lead.lead_created_time or lead.created_at)
        name = lead.full_name or "-"
        phone = lead.phone or "-"
        lines.append(f"- <b>{name}</b> | {phone} | {date_str}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=client_archive_kb(form_id, page, has_prev=has_prev, has_next=has_next),
    )
