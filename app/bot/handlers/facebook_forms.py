from datetime import datetime
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.facebook_forms_kb import (
    clients_select_kb, form_card_kb, forms_list_kb, forms_menu_kb
)
from app.bot.keyboards.leads_kb import leads_list_kb
from app.bot.states.facebook_form_states import AddFormFSM
from app.services.client_service import list_clients
from app.services.facebook_form_service import (
    create_form, get_form_by_id, list_forms, toggle_form_status
)
from app.services.lead_service import list_leads_by_form

router = Router(name="facebook_forms")


@router.callback_query(lambda c: c.data == "forms:menu")
async def forms_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    forms = await list_forms(session)
    active = [f for f in forms if f.status == "active"]
    today = datetime.now().date().isoformat()
    today_count = sum(
        1 for f in forms for l in f.leads if l.created_at.date().isoformat() == today
    )
    text = (
        f"📋 <b>FB формы</b>\n\n"
        f"Подключено: {len(forms)}\n"
        f"Активных: {len(active)}\n"
        f"Лидов сегодня: {today_count}"
    )
    await callback.message.edit_text(text, reply_markup=forms_menu_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "forms:add")
async def forms_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddFormFSM.name)
    await callback.message.edit_text("📋 <b>Добавление формы</b>\n\nШаг 1/5. Название формы:")
    await callback.answer()


@router.message(AddFormFSM.name)
async def forms_add_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(AddFormFSM.fb_page_id)
    await message.answer("Шаг 2/5. <b>FB Page ID</b>:")


@router.message(AddFormFSM.fb_page_id)
async def forms_add_page_id(message: Message, state: FSMContext) -> None:
    await state.update_data(fb_page_id=message.text.strip())
    await state.set_state(AddFormFSM.fb_form_id)
    await message.answer("Шаг 3/5. <b>FB Form ID</b>:")


@router.message(AddFormFSM.fb_form_id)
async def forms_add_form_id(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.update_data(fb_form_id=message.text.strip())
    await state.set_state(AddFormFSM.client_id)
    clients = await list_clients(session, active_only=True)
    if not clients:
        await message.answer("⚠️ Нет активных клиентов. Сначала добавь клиента.")
        await state.clear()
        return
    await message.answer("Шаг 4/5. Выбери клиента:", reply_markup=clients_select_kb(clients))


@router.callback_query(lambda c: c.data.startswith("forms:select_client:"))
async def forms_select_client(callback: CallbackQuery, state: FSMContext) -> None:
    client_id = int(callback.data.split(":")[2])
    await state.update_data(client_id=client_id)
    await state.set_state(AddFormFSM.offer_name)
    await callback.message.edit_text("Шаг 5/5. Оффер / заметка (или /skip):")
    await callback.answer()


@router.message(AddFormFSM.offer_name)
async def forms_add_offer(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    offer = message.text.strip() if message.text.strip() != "/skip" else None
    form = await create_form(
        session,
        name=data["name"],
        fb_page_id=data["fb_page_id"],
        fb_form_id=data["fb_form_id"],
        client_id=data["client_id"],
        offer_name=offer,
    )
    await state.clear()
    await message.answer(
        f"✅ Форма <b>{form.name}</b> добавлена!\n"
        f"Form ID: <code>{form.fb_form_id}</code>\n"
        f"Page ID: <code>{form.fb_page_id}</code>",
        reply_markup=form_card_kb(form.id),
    )


@router.callback_query(lambda c: c.data == "forms:list")
async def forms_list(callback: CallbackQuery, session: AsyncSession) -> None:
    forms = await list_forms(session)
    if not forms:
        await callback.answer("Форм нет. Добавь первую.", show_alert=True)
        return
    await callback.message.edit_text("📋 Список форм:", reply_markup=forms_list_kb(forms))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("forms:card:"))
async def form_card(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[2])
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена.", show_alert=True)
        return
    today = datetime.now().date().isoformat()
    leads_today = [l for l in form.leads if l.created_at.date().isoformat() == today]
    errors_today = [l for l in leads_today if l.delivery_error]
    text = (
        f"📋 <b>{form.name}</b>\n\n"
        f"FB Form ID: <code>{form.fb_form_id}</code>\n"
        f"FB Page ID: <code>{form.fb_page_id}</code>\n"
        f"Клиент: {form.client.name if form.client else '—'}\n"
        f"Оффер: {form.offer_name or '—'}\n\n"
        f"Сегодня:\n"
        f"Лидов: {len(leads_today)}\n"
        f"Ошибок: {len(errors_today)}"
    )
    await callback.message.edit_text(text, reply_markup=form_card_kb(form.id, form.status == "active"))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("forms:toggle:"))
async def form_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[2])
    form = await toggle_form_status(session, form_id)
    if not form:
        await callback.answer("Форма не найдена.", show_alert=True)
        return
    status = "активирована" if form.status == "active" else "отключена"
    await callback.answer(f"Форма {status}.", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=form_card_kb(form.id, form.status == "active"))


@router.callback_query(lambda c: c.data.startswith("forms:leads:"))
async def form_leads(callback: CallbackQuery, session: AsyncSession) -> None:
    form_id = int(callback.data.split(":")[2])
    leads = await list_leads_by_form(session, form_id)
    if not leads:
        await callback.answer("Лидов по этой форме нет.", show_alert=True)
        return
    await callback.message.edit_text(
        f"📥 Лиды формы ({len(leads)}):",
        reply_markup=leads_list_kb(leads, back_cb=f"forms:card:{form_id}"),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "forms:test")
async def forms_test(callback: CallbackQuery, session: AsyncSession) -> None:
    forms = await list_forms(session, active_only=True)
    if not forms:
        await callback.answer("Нет активных форм.", show_alert=True)
        return
    await callback.message.edit_text("Выбери форму для теста:", reply_markup=forms_list_kb(forms))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("forms:test_lead:"))
async def form_test_lead(callback: CallbackQuery, session: AsyncSession) -> None:
    import json as _json
    form_id = int(callback.data.split(":")[2])
    form = await get_form_by_id(session, form_id)
    if not form:
        await callback.answer("Форма не найдена.", show_alert=True)
        return
    from app.services.lead_service import create_lead
    from app.services.delivery_service import deliver_lead
    test_lead = await create_lead(
        session,
        client_id=form.client_id,
        facebook_form_id=form.id,
        fb_lead_id=None,
        full_name="Test User",
        phone="+1234567890",
        email="test@example.com",
        raw_data_json=_json.dumps({"test": True}),
    )
    await deliver_lead(session, callback.bot, test_lead)
    await callback.answer("✅ Тестовый лид отправлен!", show_alert=True)
