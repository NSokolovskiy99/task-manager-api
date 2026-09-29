import asyncio
import sys
from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import settings

# psycopg (async-драйвер PostgreSQL) не работает с ProactorEventLoop на Windows.
# Переключаем политику на SelectorEventLoop (совместимо с psycopg и aiosqlite).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 1. Выбор URL в зависимости от режима
if settings.DATABASE_MODE == "postgres":
    DATABASE_URL = settings.DATABASE_URL
else:
    DATABASE_URL = settings.SQLITE_URL

# 2. Создание движка (Engine)
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# 3. Фабрика сессий (Session Factory)
new_session = async_sessionmaker(engine, expire_on_commit=False)


# 4. Базовый класс моделей
class Model(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with new_session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db)]