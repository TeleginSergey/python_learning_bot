import json

from db.model.task import Task
import ast
import subprocess
import os
import asyncio
import uuid
import re


def extract_function_name(user_code: str) -> str | None:
    try:
        tree = ast.parse(user_code)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                return node.name
        return None
    except SyntaxError:
        return None


async def run_user_function(user_code: str, func_name: str, test_args: tuple, restricted_dir='/env/restricted_dir',
                            username='limiteduser') -> str:
    test_code = f"""
{user_code}

result = {func_name}{test_args}
print(result)
"""
    script_name = f'script_{uuid.uuid4()}.py'
    script_path = os.path.join(restricted_dir, script_name)

    if os.path.exists(script_path):
        os.remove(script_path)

    with open(script_path, 'w') as f:
        f.write(test_code)

    # Correcting the chown command
    subprocess.run(['sudo', 'chown', username, script_path], check=True)
    subprocess.run(['sudo', 'chmod', '500', script_path], check=True)

    proc = await asyncio.create_subprocess_exec(
        'sudo', '-u', username, 'env', 'python3', script_path,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if os.path.exists(script_path):
        os.remove(script_path)
    return stdout.decode().strip(), stderr.decode().strip()


async def check_user_task_solution(user_code: str, task: Task) -> str:
    func_name = extract_function_name(user_code)
    if not func_name:
        return "Ошибка: Функция не найдена в коде."

    input_data = json.loads(task.input_data)
    correct_answers = json.loads(task.correct_answer)

    for test_args, expected_output in zip(input_data, correct_answers):
        result, err = await run_user_function(user_code, func_name, tuple(test_args))
        if err:
            cleaned_message = re.sub(r'\n.*<module>', '', err).strip()
            return f'<b>Ваш код выдал ошибку</b>:\n{cleaned_message}'
        if str(result) != str(expected_output):
            return "Решение неверное ❌"

    secret_input = json.loads(task.secret_input)
    secret_answers = json.loads(task.secret_answer)

    for test_args, expected_output_secret in zip(secret_input, secret_answers):
        result_secret, err = await run_user_function(user_code, func_name, tuple(test_args))
        if err:
            cleaned_message = re.sub(r'\n.*<module>', '', err).strip()
            return f'<b>Ваш код выдал ошибку</b>:\n{cleaned_message}'
        if str(result_secret) != str(expected_output_secret):
            return "Решение неверное ❌"

    return f"Решение верное! Правильные ответы: {expected_output}, ваши ответы: {result}"

