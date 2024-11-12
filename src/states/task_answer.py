from aiogram.fsm.state import StatesGroup, State


class TaskAnswerState(StatesGroup):
    waiting_for_answer = State()
