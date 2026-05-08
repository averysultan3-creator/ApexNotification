from aiogram.fsm.state import State, StatesGroup


class DeliveryRuleCreate(StatesGroup):
    form_id = State()
    client_id = State()
    send_to_admin = State()
    telegram_ids = State()
    emails = State()
    google_sheet_id = State()
