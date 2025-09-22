from aiogram.fsm.state import State, StatesGroup

class CreateBoxStates(StatesGroup):
    NAME = State()
    CHANNEL = State()
    CONFIRM = State()
    ADD_CHANNEL = State()  # Новое состояние для добавления канала

class AddAdminStates(StatesGroup):
    ASK_USER = State()

class RemoveAdminStates(StatesGroup):
    ASK_USER = State()
    CONFIRM = State()

class TransferAdminStates(StatesGroup):
    ASK_USER = State()

class ButtonConfigStates(StatesGroup):
    MAIN = State()
    EDIT_BUTTON = State()
    ADD_BUTTON = State()
    CONFIRM_DELETE = State()

class AntispamStates(StatesGroup):
    MAILBOX_SELECTED = State()
