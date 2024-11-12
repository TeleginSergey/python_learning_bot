from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import Boolean

from router import router
from src.states.task_answer import TaskAnswerState
from src.utils import check_code


@router.message(TaskAnswerState.waiting_for_answer)
async def process_answer(message: Message, state: FSMContext):
    python_code = message.text
    data = await state.get_data()
    task_id = data.get('task_id')
    await check_code(message, python_code, task_id)
    await state.clear()
