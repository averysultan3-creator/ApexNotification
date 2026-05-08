from aiogram.fsm.state import State, StatesGroup


class FacebookFormCreate(StatesGroup):
    name = State()
    fb_page_id = State()
    fb_form_id = State()
    client_id = State()
    offer_name = State()
