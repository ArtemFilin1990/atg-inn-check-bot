from aiogram.fsm.state import State, StatesGroup

class InnForm(StatesGroup):
    waiting_inn = State()
