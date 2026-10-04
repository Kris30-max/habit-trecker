from aiogram.fsm.state import State, StatesGroup


class AddHabit(StatesGroup):
    title = State()
    days = State()
    remind_time = State()


class EditHabit(StatesGroup):
    title = State()
    days = State()
    remind_time = State()


class SettingsForm(StatesGroup):
    summary_time = State()
    timezone = State()
