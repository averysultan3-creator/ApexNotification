from aiogram.fsm.state import State, StatesGroup


class PrelandCreate(StatesGroup):
    name = State()
    slug = State()
    url = State()
    client_id = State()
    offer_name = State()
