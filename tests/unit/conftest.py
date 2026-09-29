"""
Фикстуры для unit-тестов.

Содержит mock-фикстуры для изоляции от реальной базы данных.
"""
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_session():
    """Создаёт mock AsyncSession для изоляции от реальной БД."""
    session = AsyncMock(spec=AsyncSession)

    # Настраиваем execute как AsyncMock, чтобы он возвращал mock result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    return session


@pytest.fixture
def sample_task_data():
    """Базовые данные для создания задачи."""
    from schemas.task import STaskAdd
    return STaskAdd(name="Test Task", description="Test Description")


@pytest.fixture
def sample_task_model():
    """Базовая модель задачи."""
    from models.tasks import TaskModel
    task = TaskModel()
    task.id = 1
    task.name = "Test Task"
    task.description = "Test Description"
    task.is_completed = False
    return task