from aiogram.fsm.state import StatesGroup, State

class WriteStates(StatesGroup):
    INPUT_TEXT = State()
    CHOOSE_TTL = State()
    PREVIEW = State()
