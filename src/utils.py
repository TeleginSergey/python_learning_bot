import json
import os
import subprocess
import tempfile

from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton


async def check_code(message: Message, user_code: str, task_id: int):
    task: Task  # TODO: Сделать select Task по task_id
    input_data = json.loads(task.input_data)  # Пример: {"args": [4], "kwargs": {}}
    args = input_data.get("args", [])
    kwargs = input_data.get("kwargs", {})

    args_str = ', '.join([str(arg) for arg in args])
    kwargs_str = ', '.join([f'{key}={value}' for key, value in kwargs.items()])
    full_params = ', '.join(filter(None, [args_str, kwargs_str]))

    code_to_execute = f"""
def user_solution(*args, **kwargs):
    {user_code}

result = user_solution({full_params})
print(result)
"""

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Отправить решение еще раз', callback_data=f'send_answer:{task_id}')],
        [InlineKeyboardButton(text='Выбрать другую задачу', callback_data='get_complexity')]
    ])

    # Создаем временный файл для хранения кода
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
        temp_file.write(code_to_execute.encode())
        temp_file_path = temp_file.name

    try:
        # Запускаем процесс
        result = subprocess.run(
            ['python3', temp_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True  # вызывает исключение при ошибке
        )
        output = result.stdout.strip()

        if output == str(eval(task.correct_answer)):  # Пример для числового ответа
            await message.answer("Ответ правильный!")
            # mark_task_as_solved(session, message.from_user.id, task.id) TODO: пометить как выполнено для пользователя
        else:
            await message.answer(f"Ответ неверный. Ожидалось: {task.correct_answer}, но получено: {output}",
                                 reply_markup=kb)
    except subprocess.CalledProcessError as e:
        await message.answer(f"Ошибка при выполнении кода: {e.stderr}", reply_markup=kb)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}", reply_markup=kb)
    finally:
        # Удаляем временный файл
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)