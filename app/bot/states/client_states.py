from aiogram.fsm.state import State, StatesGroup


class AddClientFSM(StatesGroup):
    name = State()


class AddTelegramIdFSM(StatesGroup):
    telegram_id = State()


class SetSheetFSM(StatesGroup):
    sheet_id = State()
    sheet_name = State()
