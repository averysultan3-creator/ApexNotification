"""FSM states for offer creation wizard and pixel wizard."""
from aiogram.fsm.state import State, StatesGroup


class OfferWizardFSM(StatesGroup):
    # Step 1 — Client
    step_client = State()        # show client list
    step_new_client = State()    # waiting for new client name

    # Step 2 — Offer name
    step_offer = State()

    # Step 3 — Lead form
    step_form = State()          # show existing forms or create
    step_new_form = State()      # waiting for new form name

    # Step 4 — Questions loop
    step_questions = State()     # question list screen
    step_q_text = State()        # waiting for question text
    step_q_type = State()        # choose question type
    step_q_opts = State()        # waiting for choice options

    # Step 5 — Traffic source
    step_source_type = State()   # choose source type
    step_source_name = State()   # waiting for source name

    # Step 6 — Pixel (optional)
    step_pixel = State()         # add or skip
    step_pixel_type = State()
    step_pixel_id = State()
    step_pixel_events = State()


class PixelWizardFSM(StatesGroup):
    select_type = State()
    enter_pixel_id = State()
    select_scope_type = State()
    select_scope_id = State()
    select_events = State()
    enter_name = State()


class CreateBotUserFSM(StatesGroup):
    waiting_tg_id = State()
    select_role = State()
    select_client = State()
    confirming = State()
