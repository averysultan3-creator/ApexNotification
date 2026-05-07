"""
handlers/admin/wizard.py — 🚀 Offer creation wizard (7 steps).

Steps:
  1. Select / create client
  2. Name the offer
  3. Select / create lead form
  4. Add questions (loop)
  5. Choose traffic source type + name
  6. Add pixel (optional)
  7. Final screen — create all objects and show link
"""
import json
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin_kb import (
    WizCb, MenuCb,
    wiz_clients_kb, wiz_forms_kb, wiz_questions_kb,
    wiz_question_type_kb, wiz_source_type_kb,
    wiz_pixel_kb, wiz_pixel_type_kb, wiz_pixel_events_kb, wiz_done_kb,
    main_menu_kb,
)
from models.lead_form_question import QuestionType
from services.client_service import get_clients_paginated, create_client
from services.offer_service import create_offer
from services.form_service import create_form, get_forms_paginated
from services.question_service import create_question
from services.referral_service import create_referral, build_start_link
from services.pixel_service import create_pixel
from states.wizard_states import OfferWizardFSM

logger = logging.getLogger(__name__)
router = Router()

# ── FSM data keys ──────────────────────────────────────────────────────────────
_CID = "wiz_client_id"
_CNAME = "wiz_client_name"
_ONAME = "wiz_offer_name"
_FID = "wiz_form_id"
_FNAME = "wiz_form_name"
_QS = "wiz_questions"          # list of question dicts
_SRC_TYPE = "wiz_src_type"
_SRC_NAME = "wiz_src_name"
_PX_TYPE = "wiz_px_type"
_PX_VAL = "wiz_px_val"
_PX_EVTS = "wiz_px_events"     # list of selected event names


# ══════════════════════════════════════════════════════════════════════════════
# Step 1 — Client
# ══════════════════════════════════════════════════════════════════════════════

async def _show_step1(target, session: AsyncSession, edit: bool = True) -> None:
    clients, _ = await get_clients_paginated(session, page_size=20)
    text = (
        "🚀 <b>Создание оффера</b>\n\n"
        "<b>Шаг 1/7 — Клиент</b>\n\n"
        "Выбери клиента или создай нового.\n\n"
        "<i>❔ Клиент — компания, для которой собираешь лиды.</i>"
    )
    kb = wiz_clients_kb(clients)
    if edit and hasattr(target, "message"):
        await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(WizCb.filter(F.step == "start"))
async def wiz_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(OfferWizardFSM.step_client)
    await _show_step1(callback, session, edit=True)
    await callback.answer()


@router.callback_query(WizCb.filter(F.step == "sel_client"), OfferWizardFSM.step_client)
async def wiz_sel_client(
    callback: CallbackQuery, callback_data: WizCb, state: FSMContext, session: AsyncSession
) -> None:
    from services.client_service import get_client_by_id
    client = await get_client_by_id(session, int(callback_data.val))
    if not client:
        await callback.answer("Клиент не найден", show_alert=True)
        return
    await state.update_data({_CID: client.id, _CNAME: client.name})
    await state.set_state(OfferWizardFSM.step_offer)
    await callback.message.edit_text(
        f"🚀 <b>Создание оффера</b>\n\n"
        f"<b>Шаг 2/7 — Оффер</b>\n\n"
        f"Клиент: <b>{client.name}</b>\n\n"
        f"Введи название оффера:\n"
        f"<i>Например: Удалённая работа PL 30+</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(WizCb.filter(F.step == "new_client"), OfferWizardFSM.step_client)
async def wiz_new_client_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OfferWizardFSM.step_new_client)
    await callback.message.edit_text(
        "🚀 <b>Создание оффера</b>\n\n"
        "<b>Шаг 1/7 — Новый клиент</b>\n\n"
        "Введи имя нового клиента:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(OfferWizardFSM.step_new_client)
async def wiz_new_client_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("❌ Имя не может быть пустым. Попробуй ещё раз:")
        return
    client = await create_client(session, name=name)
    await state.update_data({_CID: client.id, _CNAME: client.name})
    await state.set_state(OfferWizardFSM.step_offer)
    await message.answer(
        f"✅ Клиент <b>{client.name}</b> создан!\n\n"
        f"<b>Шаг 2/7 — Оффер</b>\n\n"
        f"Введи название оффера:",
        parse_mode="HTML",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Step 2 — Offer name
# ══════════════════════════════════════════════════════════════════════════════

@router.message(OfferWizardFSM.step_offer)
async def wiz_offer_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("❌ Название не может быть пустым. Попробуй ещё раз:")
        return
    await state.update_data({_ONAME: name})
    await state.set_state(OfferWizardFSM.step_form)
    # Show step 3 — forms
    data = await state.get_data()
    client_id = data[_CID]
    forms, _ = await get_forms_paginated(session, client_id=client_id, page_size=20)
    await message.answer(
        f"<b>Шаг 3/7 — Лидформа</b>\n\n"
        f"Оффер: <b>{name}</b>\n\n"
        f"Создать новую форму или выбрать готовую?",
        reply_markup=wiz_forms_kb(forms),
        parse_mode="HTML",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Step 3 — Form
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(WizCb.filter(F.step == "sel_form"), OfferWizardFSM.step_form)
async def wiz_sel_form(
    callback: CallbackQuery, callback_data: WizCb, state: FSMContext, session: AsyncSession
) -> None:
    from services.form_service import get_form_by_id
    form = await get_form_by_id(session, int(callback_data.val))
    if not form:
        await callback.answer("Форма не найдена", show_alert=True)
        return
    await state.update_data({_FID: form.id, _FNAME: form.name, _QS: []})
    await state.set_state(OfferWizardFSM.step_source_type)
    await _show_step5(callback, state)
    await callback.answer()


@router.callback_query(WizCb.filter(F.step == "new_form"), OfferWizardFSM.step_form)
async def wiz_new_form_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OfferWizardFSM.step_new_form)
    await callback.message.edit_text(
        "🚀 <b>Создание оффера</b>\n\n"
        "<b>Шаг 3/7 — Новая форма</b>\n\n"
        "Введи название формы:\n"
        "<i>Например: UA 30+ / PL работа</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(OfferWizardFSM.step_new_form)
async def wiz_new_form_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("❌ Название не может быть пустым. Попробуй ещё раз:")
        return
    await state.update_data({_FNAME: name, _FID: None, _QS: []})
    await state.set_state(OfferWizardFSM.step_questions)
    await message.answer(
        f"<b>Шаг 4/7 — Вопросы</b>\n\n"
        f"Форма: <b>{name}</b>\n\n"
        f"Добавь вопросы, которые должен пройти человек.\n"
        f"Нажми ➕ Добавить вопрос или ✅ Готово, чтобы пропустить.",
        reply_markup=wiz_questions_kb([]),
        parse_mode="HTML",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Step 4 — Questions loop
# ══════════════════════════════════════════════════════════════════════════════

async def _show_questions_screen(target, questions: list, edit: bool = True) -> None:
    count = len(questions)
    text = (
        f"<b>Шаг 4/7 — Вопросы</b>\n\n"
        f"Добавлено вопросов: <b>{count}</b>\n\n"
    )
    if questions:
        for i, q in enumerate(questions, 1):
            text += f"{i}. {q['text'][:40]} <i>({q['type']})</i>\n"
    else:
        text += "<i>Вопросов пока нет.</i>\n"
    text += "\nНажми ➕ чтобы добавить или ✅ Готово."
    kb = wiz_questions_kb(questions)
    if edit and hasattr(target, "message"):
        await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(WizCb.filter(F.step == "q_add"), OfferWizardFSM.step_questions)
async def wiz_q_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OfferWizardFSM.step_q_text)
    await callback.message.edit_text(
        "➕ <b>Новый вопрос</b>\n\n"
        "Введи текст вопроса:\n"
        "<i>Например: Укажи свой возраст</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(OfferWizardFSM.step_q_text)
async def wiz_q_text(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if not text:
        await message.answer("❌ Текст вопроса не может быть пустым:")
        return
    await state.update_data({"_tmp_q_text": text})
    await state.set_state(OfferWizardFSM.step_q_type)
    await message.answer(
        f"Вопрос: <b>{text}</b>\n\nВыбери тип ответа:",
        reply_markup=wiz_question_type_kb(),
        parse_mode="HTML",
    )


@router.callback_query(WizCb.filter(F.step == "q_type"), OfferWizardFSM.step_q_type)
async def wiz_q_type(
    callback: CallbackQuery, callback_data: WizCb, state: FSMContext
) -> None:
    qtype = callback_data.val
    data = await state.get_data()
    q_text = data.get("_tmp_q_text", "")

    if qtype in ("single_choice", "multi_choice"):
        await state.update_data({"_tmp_q_type": qtype})
        await state.set_state(OfferWizardFSM.step_q_opts)
        await callback.message.edit_text(
            f"Вопрос: <b>{q_text}</b>\n"
            f"Тип: <b>{qtype}</b>\n\n"
            f"Введи варианты ответов, каждый с новой строки:\n"
            f"<i>Например:\nДо 24\n25-34\n35+</i>",
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Non-choice question — add it directly
    questions = data.get(_QS, [])
    questions.append({"text": q_text, "type": qtype, "options": [], "required": True})
    await state.update_data({_QS: questions})
    await state.set_state(OfferWizardFSM.step_questions)
    await _show_questions_screen(callback, questions)
    await callback.answer()


@router.message(OfferWizardFSM.step_q_opts)
async def wiz_q_opts(message: Message, state: FSMContext) -> None:
    options = [o.strip() for o in message.text.strip().splitlines() if o.strip()]
    if len(options) < 2:
        await message.answer("❌ Нужно минимум 2 варианта. Введи каждый с новой строки:")
        return
    data = await state.get_data()
    q_text = data.get("_tmp_q_text", "")
    q_type = data.get("_tmp_q_type", "single_choice")
    questions = data.get(_QS, [])
    questions.append({"text": q_text, "type": q_type, "options": options, "required": True})
    await state.update_data({_QS: questions})
    await state.set_state(OfferWizardFSM.step_questions)
    await _show_questions_screen(message, questions, edit=False)


@router.callback_query(WizCb.filter(F.step == "q_del"), OfferWizardFSM.step_questions)
async def wiz_q_del(
    callback: CallbackQuery, callback_data: WizCb, state: FSMContext
) -> None:
    data = await state.get_data()
    questions = data.get(_QS, [])
    idx = int(callback_data.val)
    if 0 <= idx < len(questions):
        questions.pop(idx)
        await state.update_data({_QS: questions})
    await _show_questions_screen(callback, questions)
    await callback.answer("Вопрос удалён")


@router.callback_query(WizCb.filter(F.step == "q_cancel"))
async def wiz_q_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    questions = data.get(_QS, [])
    await state.set_state(OfferWizardFSM.step_questions)
    await _show_questions_screen(callback, questions)
    await callback.answer()


@router.callback_query(WizCb.filter(F.step == "q_done"), OfferWizardFSM.step_questions)
async def wiz_q_done(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OfferWizardFSM.step_source_type)
    await _show_step5(callback, state)
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
# Step 5 — Traffic source
# ══════════════════════════════════════════════════════════════════════════════

async def _show_step5(target, state: FSMContext) -> None:
    text = (
        "<b>Шаг 5/7 — Источник трафика</b>\n\n"
        "Откуда будет идти трафик?\n\n"
        "<i>❔ Источник — это канал, по которому люди переходят в бот. "
        "Например: Facebook, TikTok, Telegram.</i>"
    )
    kb = wiz_source_type_kb()
    if hasattr(target, "message"):
        await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(WizCb.filter(F.step == "src_type"), OfferWizardFSM.step_source_type)
async def wiz_src_type(
    callback: CallbackQuery, callback_data: WizCb, state: FSMContext
) -> None:
    await state.update_data({_SRC_TYPE: callback_data.val})
    await state.set_state(OfferWizardFSM.step_source_name)
    src_labels = {
        "facebook": "Facebook", "instagram": "Instagram",
        "tiktok": "TikTok", "telegram": "Telegram",
        "google": "Google", "other": "Другое",
    }
    label = src_labels.get(callback_data.val, callback_data.val)
    await callback.message.edit_text(
        f"<b>Шаг 5/7 — Источник: {label}</b>\n\n"
        f"Введи название источника:\n"
        f"<i>Например: fb12_story02 или tg_channel01</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(OfferWizardFSM.step_source_name)
async def wiz_src_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("❌ Название не может быть пустым:")
        return
    await state.update_data({_SRC_NAME: name})
    await state.set_state(OfferWizardFSM.step_pixel)
    await message.answer(
        f"<b>Шаг 6/7 — Пиксель / события</b>\n\n"
        f"Источник: <b>{name}</b>\n\n"
        f"Хочешь настроить отслеживание конверсий?\n\n"
        f"<i>❔ Пиксель позволяет понять, какой источник даёт реальные "
        f"заявки и approved-лиды.</i>",
        reply_markup=wiz_pixel_kb(),
        parse_mode="HTML",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Step 6 — Pixel (optional)
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(WizCb.filter(F.step == "px_skip"), OfferWizardFSM.step_pixel)
async def wiz_px_skip(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.update_data({_PX_TYPE: None, _PX_VAL: None, _PX_EVTS: []})
    await _wiz_finalize(callback, state, session)
    await callback.answer()


@router.callback_query(WizCb.filter(F.step == "px_add"), OfferWizardFSM.step_pixel)
async def wiz_px_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OfferWizardFSM.step_pixel_type)
    await callback.message.edit_text(
        "🎯 <b>Добавить пиксель</b>\n\nВыбери тип:",
        reply_markup=wiz_pixel_type_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(WizCb.filter(F.step == "px_type"), OfferWizardFSM.step_pixel_type)
async def wiz_px_type(
    callback: CallbackQuery, callback_data: WizCb, state: FSMContext
) -> None:
    await state.update_data({_PX_TYPE: callback_data.val, _PX_EVTS: []})
    await state.set_state(OfferWizardFSM.step_pixel_id)
    labels = {"meta": "Meta Pixel ID", "google": "Google Tag ID", "tiktok": "TikTok Pixel ID"}
    label = labels.get(callback_data.val, "Pixel ID")
    if callback_data.val == "telegram":
        # No external ID needed for telegram-only
        await state.update_data({_PX_VAL: ""})
        await state.set_state(OfferWizardFSM.step_pixel_events)
        await callback.message.edit_text(
            "🎯 <b>Telegram tracking</b>\n\n"
            "Выбери события для отслеживания:",
            reply_markup=wiz_pixel_events_kb([]),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            f"🎯 <b>Введи {label}</b>\n\n"
            f"Например: <code>123456789012345</code>",
            parse_mode="HTML",
        )
    await callback.answer()


@router.message(OfferWizardFSM.step_pixel_id)
async def wiz_px_id(message: Message, state: FSMContext) -> None:
    px_val = message.text.strip()
    if not px_val:
        await message.answer("❌ ID не может быть пустым:")
        return
    await state.update_data({_PX_VAL: px_val, _PX_EVTS: []})
    await state.set_state(OfferWizardFSM.step_pixel_events)
    await message.answer(
        "✅ ID сохранён.\n\nКакие события отправлять?\n"
        "<i>По умолчанию выбраны основные события.</i>",
        reply_markup=wiz_pixel_events_kb(["bot_started", "form_started", "lead_created", "approved"]),
        parse_mode="HTML",
    )


@router.callback_query(WizCb.filter(F.step == "sel_evt"), OfferWizardFSM.step_pixel_events)
async def wiz_sel_evt(
    callback: CallbackQuery, callback_data: WizCb, state: FSMContext
) -> None:
    data = await state.get_data()
    events = list(data.get(_PX_EVTS, []))
    evt = callback_data.val
    if evt in events:
        events.remove(evt)
    else:
        events.append(evt)
    await state.update_data({_PX_EVTS: events})
    await callback.message.edit_reply_markup(reply_markup=wiz_pixel_events_kb(events))
    await callback.answer()


@router.callback_query(WizCb.filter(F.step == "px_done"), OfferWizardFSM.step_pixel_events)
async def wiz_px_done(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await _wiz_finalize(callback, state, session)
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
# Step 7 — Finalize: create all objects in DB
# ══════════════════════════════════════════════════════════════════════════════

async def _wiz_finalize(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()

    client_id: int = data[_CID]
    client_name: str = data[_CNAME]
    offer_name: str = data[_ONAME]
    form_id: int | None = data.get(_FID)
    form_name: str = data[_FNAME]
    questions: list = data.get(_QS, [])
    src_type: str = data.get(_SRC_TYPE, "other")
    src_name: str = data.get(_SRC_NAME, "source")
    px_type: str | None = data.get(_PX_TYPE)
    px_val: str | None = data.get(_PX_VAL)
    px_events: list = data.get(_PX_EVTS, [])

    try:
        # 1. Create offer
        offer = await create_offer(session, client_id=client_id, name=offer_name)

        # 2. Create form (if new)
        if form_id is None:
            form = await create_form(session, offer_id=offer.id, name=form_name)
            form_id = form.id
        else:
            form = None

        # 3. Create questions
        for pos, q in enumerate(questions, start=1):
            opts_json = json.dumps(q["options"]) if q.get("options") else None
            await create_question(
                session,
                form_id=form_id,
                question_text=q["text"],
                question_type=q["type"],
                options_json=opts_json,
                is_required=q.get("required", True),
                position=pos,
            )

        # 4. Create referral source
        ref = await create_referral(
            session, form_id=form_id, name=src_name, source_type=src_type
        )

        # 5. Create pixel (optional)
        pixel_label = "—"
        if px_type:
            events_str = ",".join(px_events) if px_events else "bot_started,lead_created"
            px = await create_pixel(
                session,
                name=f"{offer_name} / {src_name}",
                pixel_type=px_type,
                pixel_value=px_val or "",
                scope_type="ref",
                scope_id=ref.id,
                events=events_str,
            )
            pixel_label = px.type_label

        await session.commit()

        link = build_start_link(form_id, ref.code)
        text = (
            "✅ <b>Оффер готов!</b>\n\n"
            f"Клиент:   <b>{client_name}</b>\n"
            f"Оффер:    <b>{offer_name}</b>\n"
            f"Форма:    <b>{form_name}</b>\n"
            f"Источник: <b>{src_name}</b>\n"
            f"Пиксель:  <b>{pixel_label}</b>\n\n"
            f"🔗 <b>Ссылка:</b>\n"
            f"<code>{link}</code>\n\n"
            f"<i>Зажми ссылку, чтобы скопировать.</i>"
        )
        await callback.message.edit_text(
            text,
            reply_markup=wiz_done_kb(form_id=form_id, ref_id=ref.id),
            parse_mode="HTML",
        )

    except Exception as exc:
        logger.error("Wizard finalize error: %s", exc, exc_info=True)
        await session.rollback()
        await callback.message.edit_text(
            f"❌ <b>Ошибка при создании:</b>\n<code>{exc}</code>\n\n"
            "Попробуй ещё раз или создай вручную.",
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
    finally:
        await state.clear()


# ══════════════════════════════════════════════════════════════════════════════
# Back / Cancel
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(WizCb.filter(F.step == "cancel"))
async def wiz_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "❌ Создание оффера отменено.",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(WizCb.filter(F.step == "back"))
async def wiz_back(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Navigate back one step in the wizard."""
    current = await state.get_state()
    if current == OfferWizardFSM.step_offer:
        await state.set_state(OfferWizardFSM.step_client)
        await _show_step1(callback, session)
    elif current == OfferWizardFSM.step_form:
        await state.set_state(OfferWizardFSM.step_offer)
        data = await state.get_data()
        await callback.message.edit_text(
            f"<b>Шаг 2/7 — Оффер</b>\n\nВведи название оффера:",
            parse_mode="HTML",
        )
    elif current == OfferWizardFSM.step_questions:
        await state.set_state(OfferWizardFSM.step_form)
        data = await state.get_data()
        client_id = data.get(_CID)
        forms, _ = await get_forms_paginated(session, client_id=client_id, page_size=20)
        await callback.message.edit_text(
            "<b>Шаг 3/7 — Лидформа</b>\n\nВыбери или создай форму:",
            reply_markup=wiz_forms_kb(forms),
            parse_mode="HTML",
        )
    elif current == OfferWizardFSM.step_source_type:
        # Go back to questions
        await state.set_state(OfferWizardFSM.step_questions)
        data = await state.get_data()
        questions = data.get(_QS, [])
        await _show_questions_screen(callback, questions)
    elif current == OfferWizardFSM.step_pixel:
        await state.set_state(OfferWizardFSM.step_source_type)
        await _show_step5(callback, state)
    else:
        # Fallback to main menu
        await state.clear()
        await callback.message.edit_text(
            "🏠 <b>ApexNotification</b>\n\n<i>Что делаем?</i>",
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(WizCb.filter(F.step == "add_src"))
async def wiz_add_src(
    callback: CallbackQuery, callback_data: WizCb, state: FSMContext, session: AsyncSession
) -> None:
    """Add another source to the same form (post-wizard shortcut)."""
    form_id_str = callback_data.val
    if not form_id_str.isdigit():
        await callback.answer("Нет данных", show_alert=True)
        return
    form_id = int(form_id_str)
    from services.form_service import get_form_by_id
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена", show_alert=True)
        return
    # Set up wizard state to go directly to step 5
    await state.clear()
    # We reuse the form, so we need client+offer info
    await state.update_data({
        _CID: form.client_id or 0,
        _CNAME: "existing",
        _ONAME: "existing",
        _FID: form.id,
        _FNAME: form.name,
        _QS: [],
    })
    await state.set_state(OfferWizardFSM.step_source_type)
    await _show_step5(callback, state)
    await callback.answer()
