import asyncio

import aio_pika
import msgpack
from aio_pika import ExchangeType, Queue
from aio_pika.exceptions import QueueEmpty
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from retry import retry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from consumer.schema.task import TaskMessage, GetTaskByIdMessage
from db.model.task import Task
from db.storage.db import get_db, async_session
from db.storage.rabbit import channel_pool

from aiogram import F

from src.handlers.user_handlers.callback.router import router
from src.states.task_answer import TaskAnswerState
from src.keyboards.user_kb import complex_kb, generate_carousel_keyboard


@router.callback_query(F.data == 'get_complexity')
async def get_complexity(callback: CallbackQuery):
    txt = 'Выберите уровень сложности'
    await callback.message.answer(text=txt, reply_markup=complex_kb)

@router.callback_query(F.data == 'get_another_task')
async def get_another_task(callback: CallbackQuery):
    txt = 'Выберите уровень сложности'
    await callback.message.edit_text(text=txt, reply_markup=complex_kb)


@router.callback_query(F.data.startswith('complexity_'))
async def get_tasks(callback: CallbackQuery):
    complexity = callback.data.split('_')[1]  # это сложность: easy, normal, hard

    async with channel_pool.acquire() as channel:  # type: aio_pika.Channel
        exchange = await channel.declare_exchange("user_tasks", ExchangeType.TOPIC, durable=True)

        await exchange.publish(
            aio_pika.Message(
                msgpack.packb(
                    TaskMessage(
                        user_id=callback.from_user.id,
                        action=f'get_tasks_by_complexity:{complexity}',
                        event='tasks'
                    )
                ),
            ),
            'user_messages',
        )
        queue = await channel.declare_queue(
            settings.USER_TASK_QUEUE_TEMPLATE.format(user_id=callback.from_user.id),
            durable=True,
        )
        retries = 3
        for _ in range(retries):
            try:
                tasks = await queue.get()
                parsed_tasks = msgpack.unpackb(tasks.body).get('tasks')
                print('parsed task:', parsed_tasks)
            except QueueEmpty:
                await asyncio.sleep(0.1)

    print('Parsed_task: ', parsed_tasks)
    kb = await generate_carousel_keyboard(parsed_tasks, f'select_task:{complexity}')
    txt = f'Сложность: <b>{complexity}</b>'
    await callback.message.edit_text(text=txt, reply_markup=kb, parse_mode='HTML')

@router.callback_query(F.data.regex(r'^select_task:[a-zA-Z]+:(next|prev):\d+$'))
async def handle_carousel(callback: CallbackQuery, ssn: AsyncSession):
    data = callback.data.split(':')
    page = int(data[3]) if len(data) > 3 else 0
    complexity = data[1]
    callback_prefix = data[0] + data[1]
    # async with channel_pool.acquire() as channel:  # type: aio_pika.Channel
    #     exchange = await channel.declare_exchange("user_tasks", ExchangeType.TOPIC, durable=True)
    #
    #     await exchange.publish(
    #         aio_pika.Message(
    #             msgpack.packb(
    #                 TaskMessage(
    #                     user_id=callback.from_user.id,
    #                     action=f'get_tasks_by_complexity:{complexity}',
    #                     event='tasks'
    #                 )
    #             ),
    #         ),
    #         'user_messages',
    #     )
    #     queue = await channel.declare_queue(
    #         settings.USER_TASK_QUEUE_TEMPLATE.format(user_id=callback.from_user.id),
    #         durable=True,
    #     )
    #     retries = 3
    #     for _ in range(retries):
    #         try:
    #             tasks = await queue.get()
    #             parsed_tasks = msgpack.unpackb(tasks.body)['tasks']
    #         except QueueEmpty:
    #             await asyncio.sleep(0.1)

    # items: list[Task]  # TODO нужно сделать select Task по Task.complexity == complexity
    items = await ssn.scalars(select(Task).where(Task.complexity == complexity))

    if items:
        keyboard = generate_carousel_keyboard(items, callback_prefix, page)
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    else:
        await callback.message.answer('Нет данных для отображения.')


@router.callback_query(F.data.startswith('select_task:'))
async def chosen_task(callback: CallbackQuery, state: FSMContext):
    print(callback)
    await state.clear()
    print(callback.data.split(':'))
    _, complexity, task_id = callback.data.split(':')
    async with channel_pool.acquire() as channel:  # type: aio_pika.Channel
        exchange = await channel.declare_exchange("user_tasks", ExchangeType.TOPIC, durable=True)

        await exchange.publish(
            aio_pika.Message(
                msgpack.packb(
                    GetTaskByIdMessage(
                        task_id=task_id,
                        user_id=callback.from_user.id,
                        action='get_task_by_id',
                        event='tasks'
                    )
                ),
            ),
            'user_messages',
        )
        queue = await channel.declare_queue(
            settings.USER_TASK_QUEUE_TEMPLATE.format(user_id=callback.from_user.id),
            durable=True,
        )
        retries = 3
        for _ in range(retries):
            try:
                q_task = await queue.get()
                task = msgpack.unpackb(q_task.body).get('task')
                print('asdasd', task)
            except QueueEmpty:
                await asyncio.sleep(1)
    # task: Task  # TODO Выбрать Task по Task.id == task_id

    # async with async_session() as db:
    #     task = await db.scalar(select(Task).where(Task.id == task_id))
    #     print(task.title)
    title_text = f"<b>Задача: {task['title']}</b>"
    complexity_text = f"Сложность: {task['complexity']}"
    description_text = f"Описание: {task['description']}"

    texts_to_send = [title_text, complexity_text, description_text]
    full_text = '\n'.join(texts_to_send)
    max_length = 4096

    task_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Отправить решение', callback_data=f'send_answer:{complexity}:{task_id}')],
        [InlineKeyboardButton(text='Выбрать другую задачу', callback_data='get_another_task')],
    ])

    if len(full_text) < max_length:
        await callback.message.edit_text(text=full_text, parse_mode='HTML', reply_markup=task_kb)
    else:
        for text in texts_to_send[:-2]:
            await callback.message.answer(text, parse_mode='HTML')
        await callback.message.answer(text=texts_to_send[-1], reply_markup=task_kb)


@router.callback_query(F.data.startswith('send_answer:'))
async def send_answer(callback: CallbackQuery, state: FSMContext):
    _, complexity, task_id = callback.data.split(':')

    await state.set_state(TaskAnswerState.waiting_for_answer)
    await state.update_data(task_id=task_id)

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назад', callback_data=f'select_task:{complexity}:{task_id}')],
    ])

    await callback.message.edit_text('Пришлите ваше решение в чат', reply_markup=back_kb)
