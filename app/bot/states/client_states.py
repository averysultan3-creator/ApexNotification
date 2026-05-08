from aiogram.fsm.state import State, StatesGroup


class ClientCreate(StatesGroup):
    name = State()


class ClientAddTelegram(StatesGroup):
    telegram_id = State()


class ClientAddEmail(StatesGroup):
    email = State()
