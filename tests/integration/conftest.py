"""
Фикстуры для интеграционных тестов.

Использует in-memory SQLite для изоляции от реальной БД.
Переопределяет зависимость get_db через app.dependency_overrides.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from database import Model, get_db
from main import app


# URL для in-memory SQLite (не трогаем реальный tasks.db)
TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture
async def test_engine():
    """Создаёт in-memory SQLite engine для тестов."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Создаём все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)

    yield engine

    # Удаляем таблицы после тестов
    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    """Создаёт сессию для теста с in-memory БД."""
    session_factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_session):
    """
    HTTP-клиент для тестирования API.

    Переопределяет зависимость get_db, чтобы тесты использовали
    in-memory SQLite вместо реального tasks.db.
    """

    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    # Используем ASGITransport для корректной работы с async
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Очищаем переопределения после теста
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def created_task(client):
    """Создаёт задачу через API и возвращает её данные."""
    response = await client.post(
        "/tasks/",
        json={"title": "Test Task", "description": "Test Description", "priority": 3},
    )
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def created_user(client):
    """Создаёт пользователя через API и возвращает его данные."""
    response = await client.post(
        "/users/",
        json={"name": "Test User", "email": "test@example.com"},
    )
    assert response.status_code == 201
    return response.json()