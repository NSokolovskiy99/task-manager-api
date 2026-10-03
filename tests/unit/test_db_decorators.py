"""
Unit-тесты для @db_transaction декоратора (utils/db_decorators.py).

Проверяем:
- Успешное выполнение
- IntegrityError → HTTPException(409) + rollback
- SQLAlchemyError → HTTPException(500) + rollback
- HTTPException пробрасывается без изменений + rollback
- Неожиданная ошибка → HTTPException(500) + rollback
- Ошибка при отсутствии session
"""
import pytest
from unittest.mock import AsyncMock
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from utils.db_decorators import db_transaction

pytestmark = pytest.mark.unit


# Вспомогательные асинхронные методы для тестирования декоратора
class MockService:
    """Класс с методами, обёрнутыми в @db_transaction."""

    @classmethod
    @db_transaction
    async def success_method(cls, session):
        """Успешный метод."""
        return {"status": "ok"}

    @classmethod
    @db_transaction
    async def integrity_error_method(cls, session):
        """Метод, выбрасывающий IntegrityError."""
        raise IntegrityError("INSERT", "params", Exception("Duplicate key"))

    @classmethod
    @db_transaction
    async def sqlalchemy_error_method(cls, session):
        """Метод, выбрасывающий SQLAlchemyError."""
        raise SQLAlchemyError("Connection failed")

    @classmethod
    @db_transaction
    async def http_exception_method(cls, session):
        """Метод, выбрасывающий HTTPException."""
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found"
        )

    @classmethod
    @db_transaction
    async def unexpected_error_method(cls, session):
        """Метод, выбрасывающий неожиданную ошибку."""
        raise ValueError("Something went wrong")


@pytest.fixture
def mock_db_session():
    """Создаёт AsyncMock с spec=AsyncSession для прохождения проверки isinstance."""
    session = AsyncMock(spec=AsyncSession)
    session.rollback = AsyncMock()
    return session


# ============================================================
# Тесты
# ============================================================

class TestDbTransaction:
    """Тесты для @db_transaction декоратора."""

    @pytest.mark.asyncio
    async def test_success(self, mock_db_session):
        """
        Arrange: метод успешно выполняется
        Act: вызов метода с @db_transaction
        Assert: метод вернул результат, rollback НЕ вызывался
        """
        result = await MockService.success_method(session=mock_db_session)

        assert result == {"status": "ok"}
        mock_db_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_integrity_error(self, mock_db_session):
        """
        Arrange: метод выбрасывает IntegrityError
        Act: вызов метода с @db_transaction
        Assert: session.rollback вызван, HTTPException(409)
        """
        with pytest.raises(HTTPException) as exc_info:
            await MockService.integrity_error_method(session=mock_db_session)

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "Нарушение ограничений базы данных" in exc_info.value.detail
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_sqlalchemy_error(self, mock_db_session):
        """
        Arrange: метод выбрасывает SQLAlchemyError
        Act: вызов метода с @db_transaction
        Assert: session.rollback вызван, HTTPException(500)
        """
        with pytest.raises(HTTPException) as exc_info:
            await MockService.sqlalchemy_error_method(session=mock_db_session)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Сбой при работе с базой данных" in exc_info.value.detail
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_http_exception_passthrough(self, mock_db_session):
        """
        Arrange: метод выбрасывает HTTPException(404)
        Act: вызов метода с @db_transaction
        Assert: HTTPException(404) пробрасывается без изменений, rollback вызывается
        """
        with pytest.raises(HTTPException) as exc_info:
            await MockService.http_exception_method(session=mock_db_session)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Not found"
        # Декоратор откатывает сессию (чтобы очистить «грязные» объекты), затем пробрасывает
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_unexpected_error(self, mock_db_session):
        """
        Arrange: метод выбрасывает ValueError
        Act: вызов метода с @db_transaction
        Assert: session.rollback вызван, HTTPException(500)
        """
        with pytest.raises(HTTPException) as exc_info:
            await MockService.unexpected_error_method(session=mock_db_session)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Внутренняя ошибка сервера" in exc_info.value.detail
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_session_in_kwargs(self):
        """
        Arrange: метод вызывается без session в kwargs
        Act: вызов метода с @db_transaction
        Assert: RuntimeError
        """
        with pytest.raises(RuntimeError) as exc_info:
            await MockService.success_method()  # без session

        assert "требует передачи 'session' в качестве именованного аргумента" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_non_session_object_rejected(self):
        """
        Arrange: вместо session передаём обычный объект
        Act: вызов метода с @db_transaction
        Assert: RuntimeError
        """
        with pytest.raises(RuntimeError) as exc_info:
            await MockService.success_method(session="not-a-session")

        assert "требует передачи 'session' в качестве именованного аргумента" in str(
            exc_info.value
        )