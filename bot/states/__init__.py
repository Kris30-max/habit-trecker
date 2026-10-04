from aiogram.fsm.state import State, StatesGroup


class AddHabit(StatesGroup):
    title = State()
    days = State()
    remind_time = State()
