from aiogram.fsm.state import State, StatesGroup


class AddFormFSM(StatesGroup):
    name = State()
    fb_page_id = State()
    fb_form_id = State()
    client_id = State()
    offer_name = State()
