import json
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.lead_form_question import LeadFormQuestion, QuestionType


async def get_questions_by_form(
    session: AsyncSession, form_id: int
) -> List[LeadFormQuestion]:
    result = await session.execute(
        select(LeadFormQuestion)
        .where(LeadFormQuestion.form_id == form_id)
        .order_by(LeadFormQuestion.position)
    )
    return list(result.scalars().all())


async def get_question_by_id(
    session: AsyncSession, question_id: int
) -> Optional[LeadFormQuestion]:
    result = await session.execute(
        select(LeadFormQuestion).where(LeadFormQuestion.id == question_id)
    )
    return result.scalar_one_or_none()


async def _next_position(session: AsyncSession, form_id: int) -> int:
    from sqlalchemy import func as sa_func

    result = await session.execute(
        select(sa_func.max(LeadFormQuestion.position)).where(
            LeadFormQuestion.form_id == form_id
        )
    )
    max_pos = result.scalar_one_or_none()
    return (max_pos or 0) + 1


async def create_question(
    session: AsyncSession,
    form_id: int,
    question_text: str,
    question_type: str = QuestionType.text.value,
    options: Optional[List[str]] = None,
    is_required: bool = True,
) -> LeadFormQuestion:
    position = await _next_position(session, form_id)
    options_json = json.dumps(options, ensure_ascii=False) if options else None
    question = LeadFormQuestion(
        form_id=form_id,
        position=position,
        question_text=question_text,
        question_type=question_type,
        options_json=options_json,
        is_required=is_required,
    )
    session.add(question)
    await session.flush()
    await session.refresh(question)
    return question


async def update_question(
    session: AsyncSession,
    question_id: int,
    question_text: Optional[str] = None,
    question_type: Optional[str] = None,
    options: Optional[List[str]] = None,
    is_required: Optional[bool] = None,
) -> Optional[LeadFormQuestion]:
    q = await get_question_by_id(session, question_id)
    if not q:
        return None
    if question_text is not None:
        q.question_text = question_text
    if question_type is not None:
        q.question_type = question_type
    if options is not None:
        q.options_json = json.dumps(options, ensure_ascii=False)
    if is_required is not None:
        q.is_required = is_required
    await session.flush()
    await session.refresh(q)
    return q


async def delete_question(session: AsyncSession, question_id: int) -> bool:
    q = await get_question_by_id(session, question_id)
    if not q:
        return False
    form_id = q.form_id
    await session.delete(q)
    await session.flush()
    # Re-number remaining questions
    remaining = await get_questions_by_form(session, form_id)
    for idx, rq in enumerate(remaining):
        rq.position = idx + 1
    await session.flush()
    return True


async def reorder_questions(
    session: AsyncSession, form_id: int, ordered_ids: List[int]
) -> List[LeadFormQuestion]:
    questions = {q.id: q for q in await get_questions_by_form(session, form_id)}
    for pos, qid in enumerate(ordered_ids, 1):
        if qid in questions:
            questions[qid].position = pos
    await session.flush()
    return await get_questions_by_form(session, form_id)
