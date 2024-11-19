import asyncio

import aio_pika
import msgpack
from aio_pika import ExchangeType
from fastapi import Depends
from fastapi.responses import JSONResponse, ORJSONResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette_context.header_keys import HeaderKeys

from .router import router
from db.storage.db import get_db
from db.storage.rabbit import channel_pool
from src.logger import logger

from starlette_context import context


@router.get("/home")
async def home(
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    return ORJSONResponse({"message": "Hello"})
