from aiogram.fsm.state import State, StatesGroup


# ── Client ──────────────────────────────────────────────────────────────────
class CreateClientFSM(StatesGroup):
    waiting_name = State()
    waiting_username = State()
    waiting_notes = State()
    confirming = State()


class EditClientFSM(StatesGroup):
    waiting_value = State()


# ── Offer ────────────────────────────────────────────────────────────────────
class CreateOfferFSM(StatesGroup):
    select_client = State()
    waiting_name = State()
    waiting_description = State()
    waiting_geo = State()
    waiting_language = State()
    confirming = State()


class EditOfferFSM(StatesGroup):
    waiting_value = State()


# ── LeadForm ─────────────────────────────────────────────────────────────────
class CreateFormFSM(StatesGroup):
    select_client = State()
    select_offer = State()
    waiting_name = State()
    waiting_language = State()
    waiting_welcome = State()
    waiting_success = State()
    confirming = State()


class EditFormFSM(StatesGroup):
    waiting_value = State()


# ── Question ─────────────────────────────────────────────────────────────────
class CreateQuestionFSM(StatesGroup):
    waiting_text = State()
    select_type = State()
    waiting_options = State()      # only for single/multi_choice
    select_required = State()
    confirming = State()


# ── Referral ─────────────────────────────────────────────────────────────────
class CreateRefFSM(StatesGroup):
    waiting_name = State()
    select_type = State()
    waiting_notes = State()
    confirming = State()


class EditRefFSM(StatesGroup):
    waiting_value = State()


# ── Lead ─────────────────────────────────────────────────────────────────────
class LeadFilterFSM(StatesGroup):
    waiting_client = State()
    waiting_offer = State()
    waiting_date_from = State()
    waiting_date_to = State()


class LeadNoteFSM(StatesGroup):
    waiting_note = State()


# ── Export ───────────────────────────────────────────────────────────────────
class ExportFSM(StatesGroup):
    select_format = State()
    waiting_date_from = State()
    waiting_date_to = State()
