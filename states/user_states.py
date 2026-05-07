from aiogram.fsm.state import State, StatesGroup


class UserFlowFSM(StatesGroup):
    # Form is being answered
    answering = State()
    # Multi-choice: collecting multiple selections before Done
    multi_choosing = State()
