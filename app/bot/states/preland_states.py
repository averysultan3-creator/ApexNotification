from aiogram.fsm.state import State, StatesGroup


class AddPrelandFSM(StatesGroup):
    name = State()
    slug = State()
    url = State()
