from aiogram.fsm.state import State, StatesGroup


class AddPrelandFSM(StatesGroup):
    """Legacy FSM kept for backward compat."""
    name = State()
    confirm = State()
    slug = State()
    url = State()


class AddSiteFSM(StatesGroup):
    """Two-step FSM: enter site name, then base URL."""
    name = State()
    base_url = State()


class AddLinkFSM(StatesGroup):
    """Create a tracking link under a site."""
    raw_name = State()   # free-text input parsed by preland_name_service
    confirm = State()    # show preview, wait for confirm / re-enter
