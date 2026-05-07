import json
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin_kb import (
    QuestionCb, CancelCb, SelectQTypeCb, FormCb, ConfirmCb,
    questions_list_kb, question_view_kb, question_type_kb,
    required_kb, cancel_kb, skip_cancel_kb, confirm_delete_kb, main_menu_kb,
)
from services.question_service import (
    get_questions_by_form, get_question_by_id, create_question, delete_question,
    reorder_questions, update_question,
)
from services.form_service import get_form_by_id
from states.admin_states import CreateQuestionFSM
from utils.formatters import fmt_question

logger = logging.getLogger(__name__)
router = Router()


# ── List ──────────────────────────────────────────────────────────────────────

@router.callback_query(QuestionCb.filter(F.action == "list"))
async def questions_list(
    callback: CallbackQuery, callback_data: QuestionCb, session: AsyncSession
) -> None:
    form_id = callback_data.form_id
    questions = await get_questions_by_form(session, form_id)
    if not questions:
        form = await get_form_by_id(session, form_id)
        form_name = form.name if form else "?"
        await callback.message.edit_text(
            f"🧩 <b>Вопросы формы «{form_name}»</b>\n\n<i>Вопросов пока нет.</i>",
            reply_markup=questions_list_kb([], form_id),
            parse_mode="HTML",
        )
    else:
        form = await get_form_by_id(session, form_id)
        text = f"🧩 <b>Вопросы формы «{form.name if form else '?'}»</b>\n\n"
        for i, q in enumerate(questions, 1):
            text += fmt_question(q, i) + "\n\n"
        await callback.message.edit_text(
            text, reply_markup=questions_list_kb(questions, form_id), parse_mode="HTML"
        )
    await callback.answer()


# ── View ──────────────────────────────────────────────────────────────────────

@router.callback_query(QuestionCb.filter(F.action == "view"))
async def question_view(
    callback: CallbackQuery, callback_data: QuestionCb, session: AsyncSession
) -> None:
    q = await get_question_by_id(session, callback_data.id)
    if not q:
        await callback.answer("Вопрос не найден", show_alert=True)
        return
    text = fmt_question(q, q.position)
    await callback.message.edit_text(
        text, reply_markup=question_view_kb(q), parse_mode="HTML"
    )
    await callback.answer()


# ── Create: wizard ────────────────────────────────────────────────────────────

@router.callback_query(QuestionCb.filter(F.action == "new"))
async def create_question_start(
    callback: CallbackQuery, callback_data: QuestionCb, state: FSMContext
) -> None:
    await state.set_state(CreateQuestionFSM.waiting_text)
    await state.update_data(form_id=callback_data.form_id)
    await callback.message.edit_text(
        "➕ <b>Добавление вопроса</b>\n\nШаг 1/3: Введите <b>текст вопроса</b>:",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateQuestionFSM.waiting_text)
async def create_question_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) < 3:
        await message.answer("❗ Вопрос слишком короткий.", reply_markup=cancel_kb())
        return
    await state.update_data(question_text=text)
    await state.set_state(CreateQuestionFSM.select_type)
    await message.answer(
        "Шаг 2/3: Выберите <b>тип вопроса</b>:",
        reply_markup=question_type_kb(),
        parse_mode="HTML",
    )


@router.callback_query(SelectQTypeCb.filter(), CreateQuestionFSM.select_type)
async def create_question_type(
    callback: CallbackQuery, callback_data: SelectQTypeCb, state: FSMContext
) -> None:
    qtype = callback_data.qtype
    await state.update_data(question_type=qtype)
    CHOICE_TYPES = {"single_choice", "multi_choice"}
    if qtype in CHOICE_TYPES:
        await state.set_state(CreateQuestionFSM.waiting_options)
        await callback.message.edit_text(
            "Введите варианты ответа (каждый на новой строке):",
            reply_markup=cancel_kb(),
            parse_mode="HTML",
        )
    else:
        await state.set_state(CreateQuestionFSM.select_required)
        await callback.message.edit_text(
            "Шаг 3/3: Вопрос обязателен?",
            reply_markup=required_kb(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.message(CreateQuestionFSM.waiting_options)
async def create_question_options(message: Message, state: FSMContext) -> None:
    raw = message.text or ""
    options = [line.strip() for line in raw.split("\n") if line.strip()]
    if len(options) < 2:
        await message.answer("❗ Введите минимум 2 варианта (каждый на новой строке):", reply_markup=cancel_kb())
        return
    await state.update_data(options=options)
    await state.set_state(CreateQuestionFSM.select_required)
    await message.answer(
        "Шаг 3/3: Вопрос обязателен?",
        reply_markup=required_kb(),
        parse_mode="HTML",
    )


@router.callback_query(CancelCb.filter(F.action.in_({"required_yes", "required_no"})))
async def create_question_required(
    callback: CallbackQuery, callback_data: CancelCb, state: FSMContext, session: AsyncSession
) -> None:
    is_required = callback_data.action == "required_yes"
    data = await state.get_data()
    question = await create_question(
        session,
        form_id=data["form_id"],
        question_text=data["question_text"],
        question_type=data["question_type"],
        options=data.get("options"),
        is_required=is_required,
    )
    await state.clear()
    await callback.message.edit_text(
        f"✅ Вопрос добавлен!\n\n{fmt_question(question, question.position)}",
        reply_markup=question_view_kb(question),
        parse_mode="HTML",
    )
    await callback.answer()


# ── Edit question text ────────────────────────────────────────────────────────

@router.callback_query(QuestionCb.filter(F.action == "edit_text"))
async def question_edit_text_start(
    callback: CallbackQuery, callback_data: QuestionCb, state: FSMContext
) -> None:
    # Reuse CreateQuestionFSM.waiting_text as edit state
    await state.set_state(CreateQuestionFSM.confirming)
    await state.update_data(question_id=callback_data.id, form_id=callback_data.form_id)
    await callback.message.edit_text(
        "✏️ Введите новый <b>текст вопроса</b>:",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateQuestionFSM.confirming)
async def question_edit_text_save(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    new_text = (message.text or "").strip()
    if len(new_text) < 3:
        await message.answer("❗ Слишком короткий текст.", reply_markup=cancel_kb())
        return
    q = await update_question(session, data["question_id"], question_text=new_text)
    await state.clear()
    if not q:
        await message.answer("❗ Вопрос не найден.", reply_markup=main_menu_kb())
        return
    await message.answer(
        f"✅ Текст обновлён!\n\n{fmt_question(q, q.position)}",
        reply_markup=question_view_kb(q),
        parse_mode="HTML",
    )


# ── Move up / down ────────────────────────────────────────────────────────────

@router.callback_query(QuestionCb.filter(F.action.in_({"move_up", "move_down"})))
async def question_move(
    callback: CallbackQuery, callback_data: QuestionCb, session: AsyncSession
) -> None:
    q = await get_question_by_id(session, callback_data.id)
    if not q:
        await callback.answer("Вопрос не найден", show_alert=True)
        return
    questions = await get_questions_by_form(session, q.form_id)
    ordered_ids = [iq.id for iq in questions]
    idx = ordered_ids.index(q.id)
    if callback_data.action == "move_up" and idx > 0:
        ordered_ids[idx], ordered_ids[idx - 1] = ordered_ids[idx - 1], ordered_ids[idx]
    elif callback_data.action == "move_down" and idx < len(ordered_ids) - 1:
        ordered_ids[idx], ordered_ids[idx + 1] = ordered_ids[idx + 1], ordered_ids[idx]
    else:
        await callback.answer("Уже на краю.", show_alert=False)
        return
    await reorder_questions(session, q.form_id, ordered_ids)
    updated = await get_questions_by_form(session, q.form_id)
    await callback.answer("✅ Порядок изменён.")
    await callback.message.edit_text(
        "🧩 <b>Вопросы обновлены</b>",
        reply_markup=questions_list_kb(updated, q.form_id),
        parse_mode="HTML",
    )


# ── Delete ────────────────────────────────────────────────────────────────────

@router.callback_query(QuestionCb.filter(F.action == "del"))
async def question_delete_confirm(
    callback: CallbackQuery, callback_data: QuestionCb, session: AsyncSession
) -> None:
    q = await get_question_by_id(session, callback_data.id)
    if not q:
        await callback.answer("Вопрос не найден", show_alert=True)
        return
    await callback.message.edit_text(
        f"🗑 Удалить вопрос:\n\n<b>{q.question_text}</b>?",
        reply_markup=confirm_delete_kb(f"question_{q.id}_{q.form_id}"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(ConfirmCb.filter(F.target.startswith("question_")))
async def question_delete_do(
    callback: CallbackQuery, callback_data: ConfirmCb, session: AsyncSession
) -> None:
    if callback_data.action != "yes":
        await callback.answer("Отменено.")
        await callback.message.edit_text("❌ Отменено.", reply_markup=main_menu_kb())
        return
    parts = callback_data.target.split("_")
    q_id = int(parts[1])
    form_id = int(parts[2])
    await delete_question(session, q_id)
    await callback.answer("✅ Вопрос удалён.")
    questions = await get_questions_by_form(session, form_id)
    await callback.message.edit_text(
        "🧩 <b>Вопросы формы</b>",
        reply_markup=questions_list_kb(questions, form_id),
        parse_mode="HTML",
    )
