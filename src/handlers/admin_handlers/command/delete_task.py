import aio_pika
import msgpack
import asyncio
from aio_pika import ExchangeType
from aiogram import F
from aio_pika.exceptions import QueueEmpty
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from consumer.schema.task import TaskMessage
from db.storage.rabbit import channel_pool
from router import router
from src.keyboards.user_kb import complex_kb
from config.settings import  settings


@router.message(Command('delete_task'))
async def delete_task(message: Message):
    await message.answer('Выберите сложность задачи, которую хотите удалить', reply_markup=complex_kb)


@router.callback_query(F.data.startswith('complexity_'))
async def get_complexity(callback: CallbackQuery):
    complexity = callback.data.split('_')[-1]
    async with channel_pool.acquire() as channel:  # type: aio_pika.Channel
        exchange = await channel.declare_exchange("admin_tasks", ExchangeType.TOPIC, durable=True)

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
            # settings.USER_TASK_QUEUE_TEMPLATE.format(
            #     user_id=callback.from_user.id,
            'user_messages',
        )

    queue = await channel.declare_queue(
        'admin_tasks.{admin_id}'.format(admin_id=callback.from_user.id),
        durable=True,
    )

    retries = 3
    for _ in range(retries):
        try:
            tasks = await queue.get()
            parsed_tasks = msgpack.unpackb(tasks.body).get('tasks')
            if parsed_tasks:
                break
        except QueueEmpty:
            await asyncio.sleep(.02)