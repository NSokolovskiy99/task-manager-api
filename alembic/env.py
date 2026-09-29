import asyncio
import selectors
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# --- Проектные импорты ---
# database.Model — базовый класс всех моделей (источник Model.metadata).
# models.tasks.TaskModel — импорт регистрирует таблицу tasks в Model.metadata,
# без него Alembic не увидит модель при --autogenerate.
# core.config.settings — выбор URL по DATABASE_MODE (postgres/sqlite).
from database import Model
from models.tasks import TaskModel  # noqa: F401  (неявное использование: регистрация таблицы)
from models.users import UserModel
from core.config import settings

# объект конфигурации Alembic
config = context.config

# настройка логирования из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Model.metadata

# --- Выбор БД по режиму (единый источник истины — core.config.settings) ---
# Тесты используют in-memory SQLite (см. tests/integration/conftest.py),
# приложение работает на PostgreSQL (DATABASE_MODE=postgres в Docker/.env).
# env.py переопределяет sqlalchemy.url из alembic.ini этим значением.
if settings.DATABASE_MODE == "postgres":
    DATABASE_URL = settings.DATABASE_URL
else:
    DATABASE_URL = settings.SQLITE_URL

config.set_main_option("sqlalchemy.url", DATABASE_URL)

# SQLite не поддерживает ALTER TABLE для добавления колонок с FK напрямую —
# включаем batch-режим (пересоздание таблицы), чтобы add_column работал.
RENDER_AS_BATCH = settings.DATABASE_MODE != "postgres"


def run_migrations_offline() -> None:
    """Запуск миграций в 'offline' режиме.

    Не требует подключения к БД — формирует SQL-скрипт.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=RENDER_AS_BATCH,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Выполнение миграций через переданное подключение."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=RENDER_AS_BATCH,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Запуск миграций в асинхронном режиме."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Запуск миграций в 'online' режиме (с подключением к БД)."""
    # psycopg (async) на Windows не работает с ProactorEventLoop.
    # SelectorEventLoop — официальная рекомендация psycopg, работает на любой ОС.
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    try:
        loop.run_until_complete(run_async_migrations())
    finally:
        loop.close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
