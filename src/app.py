import asyncio
import logging

from aiogram import Dispatcher, Bot
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.orm import sessionmaker

from config.settings import settings
from db.storage.db import async_session
from src.bot import setup_bot, setup_dp
from src.logger import LOGGING_CONFIG, logger
from db.storage.redis import setup_redis
from src.rabbit_initializer import init_rabbitmq

from src.handlers.user_handlers.command.router import router as user_command_start_router
from src.handlers.user_handlers.callback.router import router as user_callback_router
from src.handlers.admin_handlers.state_handlers.router import router as admin_state_router
from src.handlers.admin_handlers.command.router import router as admin_cmd_router


async def start_polling():
    logging.config.dictConfig(LOGGING_CONFIG)

    logger.info('Starting polling')
    redis = setup_redis()
    storage = RedisStorage(redis=redis)
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=storage)
    setup_dp(dp)
    setup_bot(bot)
    dp.include_router(admin_cmd_router)
    dp.include_router(admin_state_router)
    dp.include_router(user_callback_router)
    dp.include_router(user_command_start_router)
    await bot.delete_webhook()
    await init_rabbitmq()

    logging.error('Dependencies launched')
    await dp.start_polling(bot, dp=async_session)


if __name__ == '__main__':
    asyncio.run(start_polling())
