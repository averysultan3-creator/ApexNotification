"""
User-facing form flow.

Deep link format: /start lf_{form_id}_ref_{ref_code}
"""
import json
import logging
from typing import Any, Dict, List

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.user_kb import start_form_kb, single_choice_kb, multi_choice_kb, skip_kb
from keyboards.admin_kb import UserFlowCb, QOptionCb
from models.lead_form_question import QuestionType, CHOICE_TYPES
from services.form_service import get_form_by_id
from services.referral_service import get_ref_by_code
from services.lead_service import create_lead, check_duplicate_lead
from services.question_service import get_questions_by_form
from services.tracking_service import (
    new_session_id,
    start_tracking_session,
    track_form_started,
    track_question_viewed,
    track_question_answered,
    track_form_completed,
    track_lead_created,
    track_duplicate_detected,
)
from states.user_states import UserFlowFSM
from utils.notifications import notify_admins_new_lead
from utils.validators import validate_phone, validate_telegram_username, validate_number, validate_date

logger = logging.getLogger(__name__)
router = Router()

# Keys used in FSM data
_FORM_ID = "uf_form_id"
_REF_ID = "uf_ref_id"
_REF_SOURCE_ID = "uf_ref_source_id"    # ReferralSource.id (not ref_id alias)
_CLIENT_ID = "uf_client_id"
_OFFER_ID = "uf_offer_id"
_QUESTIONS = "uf_questions"   # serialized list of question dicts
_CUR_IDX = "uf_cur_idx"
_ANSWERS = "uf_answers"        # dict: question_text -> answer_str
_MULTI_SEL = "uf_multi_sel"    # list of selected indices for current multi-choice
_SESSION_ID = "uf_session_id"  # tracking session ID
_TG_USER_ID = "uf_tg_user_id"  # telegram_user_id for tracking


def _serialize_question(q) -> dict:
    return {
        "id": q.id,
        "text": q.question_text,
        "type": q.question_type,
        "options": json.loads(q.options_json) if q.options_json else [],
        "required": q.is_required,
    }


async def _safe_track(coro) -> None:
    """Execute a tracking coroutine silently — never breaks user flow."""
    try:
        await coro
    except Exception as exc:
        logger.debug("Tracking error (non-critical): %s", exc)


async def _ask_question(
    message: Message,
    q: dict,
    state: FSMContext,
    edit: bool = False,
) -> None:
    q_type = q["type"]
    text = q["text"]
    options: List[str] = q["options"]
    is_required: bool = q["required"]

    hint = ""
    if q_type == QuestionType.phone.value:
        hint = "\n\n<i>Введите номер телефона (напр. +380971234567)</i>"
    elif q_type == QuestionType.telegram_username.value:
        hint = "\n\n<i>Введите Telegram username (напр. @username)</i>"
    elif q_type == QuestionType.number.value:
        hint = "\n\n<i>Введите числовое значение</i>"
    elif q_type == QuestionType.date.value:
        hint = "\n\n<i>Введите дату в формате дд.мм.гггг</i>"

    full_text = f"❓ <b>{text}</b>{hint}"
    skip_marker = "" if is_required else "\n\n<i>(необязательный, можно пропустить)</i>"
    full_text += skip_marker

    if q_type == QuestionType.single_choice.value:
        kb = single_choice_kb(options)
    elif q_type == QuestionType.multi_choice.value:
        await state.update_data(**{_MULTI_SEL: []})
        await state.set_state(UserFlowFSM.multi_choosing)
        kb = multi_choice_kb(options, [])
    else:
        await state.set_state(UserFlowFSM.answering)
        kb = skip_kb() if not is_required else None

    if kb:
        await message.answer(full_text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(full_text, parse_mode="HTML")


async def _save_and_finish(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    data = await state.get_data()
    form_id = data[_FORM_ID]
    ref_id = data.get(_REF_ID)
    client_id = data[_CLIENT_ID]
    offer_id = data[_OFFER_ID]
    answers: dict = data.get(_ANSWERS, {})
    session_id = data.get(_SESSION_ID, "")
    tg_user_id = data.get(_TG_USER_ID)

    _tk = dict(
        session_id=session_id, form_id=form_id, client_id=client_id,
        offer_id=offer_id, referral_source_id=ref_id, telegram_user_id=tg_user_id,
    )

    await _safe_track(track_form_completed(session, **_tk))

    user = message.from_user
    try:
        lead = await create_lead(
            session,
            form_id=form_id,
            client_id=client_id,
            offer_id=offer_id,
            referral_source_id=ref_id,
            telegram_user_id=user.id,
            telegram_username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            answers=answers,
        )
        logger.info(
            "Lead created: id=%s form_id=%s user_id=%s ref_id=%s",
            lead.id, form_id, user.id, ref_id,
        )
        await _safe_track(track_lead_created(session, lead_id=lead.id, **_tk))
    except Exception as exc:
        logger.error("Failed to save lead: form_id=%s user_id=%s error=%s", form_id, user.id, exc, exc_info=True)
        await message.answer("❗ Произошла ошибка при сохранении заявки. Попробуйте позже.")
        return

    form = await get_form_by_id(session, form_id)
    success_text = (form.success_text if form and form.success_text
                    else "✅ Спасибо! Ваша заявка принята.")
    await state.clear()
    await message.answer(success_text, parse_mode="HTML")

    # Notify admins
    await notify_admins_new_lead(bot, lead)


# ── /start handler ────────────────────────────────────────────────────────────

@router.message(CommandStart(deep_link=True))
async def user_start_deep(
    message: Message, command: CommandObject, state: FSMContext, session: AsyncSession
) -> None:
    payload = command.args or ""
    # Expected: lf_{form_id}_ref_{ref_code}
    parts = payload.split("_")
    if len(parts) != 4 or parts[0] != "lf" or parts[2] != "ref":
        logger.warning("Invalid deep link payload from user_id=%s: %r", message.from_user.id, payload)
        await message.answer("❗ Неверная ссылка. Обратитесь к тому, кто вам её дал.")
        return

    try:
        form_id = int(parts[1])
        ref_code = parts[3]
    except (ValueError, IndexError):
        logger.warning("Malformed deep link from user_id=%s: %r", message.from_user.id, payload)
        await message.answer("❗ Неверный формат ссылки.")
        return

    form = await get_form_by_id(session, form_id)
    if not form or form.status != "active":
        logger.info("Form %s not found or inactive (user_id=%s)", form_id, message.from_user.id)
        await message.answer("❗ Форма недоступна или отключена.")
        return

    # Check client and offer are active
    if not form.client or form.client.status != "active":
        await message.answer("❗ Форма временно недоступна.")
        return
    if not form.offer or form.offer.status != "active":
        await message.answer("❗ Форма временно недоступна.")
        return

    ref = await get_ref_by_code(session, ref_code)
    if not ref or ref.status != "active":
        await message.answer("❗ Источник трафика недоступен.")
        return

    # Check duplicate
    is_dup = await check_duplicate_lead(session, form_id, message.from_user.id)
    if is_dup:
        # Create tracking session for duplicate
        dup_sid = new_session_id()
        await _safe_track(start_tracking_session(
            session, session_id=dup_sid, form_id=form_id,
            client_id=form.client_id, offer_id=form.offer_id,
            referral_source_id=ref.id,
            telegram_user_id=message.from_user.id,
            telegram_username=message.from_user.username,
            total_steps=0,
        ))
        await _safe_track(track_duplicate_detected(
            session, dup_sid,
            form_id=form_id, client_id=form.client_id, offer_id=form.offer_id,
            referral_source_id=ref.id,
            telegram_user_id=message.from_user.id,
            telegram_username=message.from_user.username,
        ))
        await message.answer("ℹ️ Вы уже заполняли эту форму. Мы с вами свяжемся!")
        return

    # Load questions
    questions_orm = await get_questions_by_form(session, form_id)
    if not questions_orm:
        await message.answer("❗ Форма не содержит вопросов. Обратитесь позднее.")
        return

    questions = [_serialize_question(q) for q in questions_orm]

    # Create tracking session (bot_started + form_viewed events emitted inside)
    session_id = new_session_id()
    await _safe_track(start_tracking_session(
        session, session_id=session_id,
        form_id=form_id, client_id=form.client_id, offer_id=form.offer_id,
        referral_source_id=ref.id,
        telegram_user_id=message.from_user.id,
        telegram_username=message.from_user.username,
        total_steps=len(questions),
    ))

    await state.clear()
    await state.update_data(**{
        _FORM_ID: form_id,
        _REF_ID: ref.id,
        _REF_SOURCE_ID: ref.id,
        _CLIENT_ID: form.client_id,
        _OFFER_ID: form.offer_id,
        _QUESTIONS: questions,
        _CUR_IDX: 0,
        _ANSWERS: {},
        _SESSION_ID: session_id,
        _TG_USER_ID: message.from_user.id,
    })

    welcome = form.welcome_text or f"Привет! Вы заполняете форму <b>{form.name}</b>."
    await message.answer(welcome, reply_markup=start_form_kb(), parse_mode="HTML")


# ── Start form ────────────────────────────────────────────────────────────────

@router.callback_query(UserFlowCb.filter(F.action == "start"))
async def flow_start(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    questions: List[dict] = data.get(_QUESTIONS, [])
    if not questions:
        await callback.answer("❗ Нет вопросов.", show_alert=True)
        return

    _tk = dict(
        form_id=data.get(_FORM_ID), client_id=data.get(_CLIENT_ID),
        offer_id=data.get(_OFFER_ID), referral_source_id=data.get(_REF_SOURCE_ID),
        telegram_user_id=data.get(_TG_USER_ID),
    )
    session_id = data.get(_SESSION_ID, "")
    await _safe_track(track_form_started(session, session_id, **_tk))
    await _safe_track(track_question_viewed(
        session, session_id, **_tk,
        question_id=questions[0].get("id"), step_number=0,
    ))

    await callback.message.delete()
    await _ask_question(callback.message, questions[0], state)
    await callback.answer()


# ── Text / phone / number / date / comment answers ────────────────────────────

@router.message(UserFlowFSM.answering)
async def flow_text_answer(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    data = await state.get_data()
    questions: List[dict] = data.get(_QUESTIONS, [])
    idx: int = data.get(_CUR_IDX, 0)
    if idx >= len(questions):
        await _save_and_finish(message, state, session, bot)
        return

    q = questions[idx]
    raw = (message.text or "").strip()
    q_type = q["type"]

    # Validate
    if q_type == QuestionType.phone.value:
        validated = validate_phone(raw)
        if not validated:
            await message.answer("❗ Неверный номер телефона. Попробуйте снова:", reply_markup=skip_kb() if not q["required"] else None)
            return
        raw = validated
    elif q_type == QuestionType.telegram_username.value:
        validated = validate_telegram_username(raw)
        if not validated:
            await message.answer("❗ Неверный username. Введите без @ или с @:", reply_markup=skip_kb() if not q["required"] else None)
            return
        raw = "@" + validated
    elif q_type == QuestionType.number.value:
        validated = validate_number(raw)
        if not validated:
            await message.answer("❗ Введите числовое значение:", reply_markup=skip_kb() if not q["required"] else None)
            return
        raw = validated
    elif q_type == QuestionType.date.value:
        validated = validate_date(raw)
        if not validated:
            await message.answer("❗ Неверная дата. Введите дд.мм.гггг:", reply_markup=skip_kb() if not q["required"] else None)
            return
        raw = validated

    answers: dict = data.get(_ANSWERS, {})
    answers[q["text"]] = raw
    next_idx = idx + 1

    session_id = data.get(_SESSION_ID, "")
    _tk = dict(
        form_id=data.get(_FORM_ID), client_id=data.get(_CLIENT_ID),
        offer_id=data.get(_OFFER_ID), referral_source_id=data.get(_REF_SOURCE_ID),
        telegram_user_id=data.get(_TG_USER_ID),
    )
    await _safe_track(track_question_answered(
        session, session_id, **_tk, question_id=q.get("id"), step_number=idx
    ))
    await state.update_data(**{_ANSWERS: answers, _CUR_IDX: next_idx})

    if next_idx >= len(questions):
        await _save_and_finish(message, state, session, bot)
    else:
        await _safe_track(track_question_viewed(
            session, session_id, **_tk,
            question_id=questions[next_idx].get("id"), step_number=next_idx,
        ))
        await _ask_question(message, questions[next_idx], state)


# ── Skip non-required question ────────────────────────────────────────────────

@router.callback_query(UserFlowCb.filter(F.action == "skip"))
async def flow_skip(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    data = await state.get_data()
    questions: List[dict] = data.get(_QUESTIONS, [])
    idx: int = data.get(_CUR_IDX, 0)
    q = questions[idx] if idx < len(questions) else None
    if q and q["required"]:
        await callback.answer("❗ Этот вопрос обязателен.", show_alert=True)
        return

    answers: dict = data.get(_ANSWERS, {})
    if q:
        answers[q["text"]] = "—"
    next_idx = idx + 1
    await state.update_data(**{_ANSWERS: answers, _CUR_IDX: next_idx})
    await callback.message.delete()

    session_id = data.get(_SESSION_ID, "")
    _tk = dict(
        form_id=data.get(_FORM_ID), client_id=data.get(_CLIENT_ID),
        offer_id=data.get(_OFFER_ID), referral_source_id=data.get(_REF_SOURCE_ID),
        telegram_user_id=data.get(_TG_USER_ID),
    )
    if q:
        await _safe_track(track_question_answered(
            session, session_id, **_tk, question_id=q.get("id"), step_number=idx
        ))

    if next_idx >= len(questions):
        await _save_and_finish(callback.message, state, session, bot)
    else:
        await _safe_track(track_question_viewed(
            session, session_id, **_tk,
            question_id=questions[next_idx].get("id"), step_number=next_idx,
        ))
        await _ask_question(callback.message, questions[next_idx], state)
    await callback.answer()


# ── Single choice answer ──────────────────────────────────────────────────────

@router.callback_query(UserFlowCb.filter(F.action == "pick"))
async def flow_pick_single(
    callback: CallbackQuery, callback_data: UserFlowCb, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    data = await state.get_data()
    questions: List[dict] = data.get(_QUESTIONS, [])
    idx: int = data.get(_CUR_IDX, 0)
    q = questions[idx] if idx < len(questions) else None
    if not q:
        await callback.answer()
        return

    val = callback_data.val
    answers: dict = data.get(_ANSWERS, {})
    answers[q["text"]] = val
    next_idx = idx + 1
    await state.update_data(**{_ANSWERS: answers, _CUR_IDX: next_idx})
    await callback.message.delete()

    session_id = data.get(_SESSION_ID, "")
    _tk = dict(
        form_id=data.get(_FORM_ID), client_id=data.get(_CLIENT_ID),
        offer_id=data.get(_OFFER_ID), referral_source_id=data.get(_REF_SOURCE_ID),
        telegram_user_id=data.get(_TG_USER_ID),
    )
    await _safe_track(track_question_answered(
        session, session_id, **_tk, question_id=q.get("id"), step_number=idx
    ))

    if next_idx >= len(questions):
        await _save_and_finish(callback.message, state, session, bot)
    else:
        await _safe_track(track_question_viewed(
            session, session_id, **_tk,
            question_id=questions[next_idx].get("id"), step_number=next_idx,
        ))
        await _ask_question(callback.message, questions[next_idx], state)
    await callback.answer()


# ── Multi-choice: toggle option ───────────────────────────────────────────────

@router.callback_query(QOptionCb.filter(), UserFlowFSM.multi_choosing)
async def flow_toggle_multi(
    callback: CallbackQuery, callback_data: QOptionCb, state: FSMContext
) -> None:
    data = await state.get_data()
    questions: List[dict] = data.get(_QUESTIONS, [])
    idx: int = data.get(_CUR_IDX, 0)
    q = questions[idx] if idx < len(questions) else None
    if not q:
        await callback.answer()
        return

    selected: List[int] = data.get(_MULTI_SEL, [])
    opt_idx = callback_data.idx
    if opt_idx in selected:
        selected.remove(opt_idx)
    else:
        selected.append(opt_idx)

    await state.update_data(**{_MULTI_SEL: selected})
    await callback.message.edit_reply_markup(
        reply_markup=multi_choice_kb(q["options"], selected)
    )
    await callback.answer()


# ── Multi-choice: done ────────────────────────────────────────────────────────

@router.callback_query(UserFlowCb.filter(F.action == "done"), UserFlowFSM.multi_choosing)
async def flow_done_multi(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    data = await state.get_data()
    questions: List[dict] = data.get(_QUESTIONS, [])
    idx: int = data.get(_CUR_IDX, 0)
    q = questions[idx] if idx < len(questions) else None
    if not q:
        await callback.answer()
        return

    selected: List[int] = data.get(_MULTI_SEL, [])
    options = q["options"]

    if q["required"] and not selected:
        await callback.answer("❗ Выберите хотя бы один вариант.", show_alert=True)
        return

    selected_labels = [options[i] for i in selected if i < len(options)]
    answer_str = ", ".join(selected_labels) if selected_labels else "—"

    answers: dict = data.get(_ANSWERS, {})
    answers[q["text"]] = answer_str
    next_idx = idx + 1
    await state.update_data(**{_ANSWERS: answers, _CUR_IDX: next_idx, _MULTI_SEL: []})
    await callback.message.delete()

    session_id = data.get(_SESSION_ID, "")
    _tk = dict(
        form_id=data.get(_FORM_ID), client_id=data.get(_CLIENT_ID),
        offer_id=data.get(_OFFER_ID), referral_source_id=data.get(_REF_SOURCE_ID),
        telegram_user_id=data.get(_TG_USER_ID),
    )
    await _safe_track(track_question_answered(
        session, session_id, **_tk, question_id=q.get("id"), step_number=idx
    ))

    if next_idx >= len(questions):
        await _save_and_finish(callback.message, state, session, bot)
    else:
        await _safe_track(track_question_viewed(
            session, session_id, **_tk,
            question_id=questions[next_idx].get("id"), step_number=next_idx,
        ))
        await _ask_question(callback.message, questions[next_idx], state)
    await callback.answer()
