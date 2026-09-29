"""
Unit-тесты для TaskRepository (services/tasks_repository.py).

Все тесты следуют паттерну Arrange-Act-Assert.
Репозиторий изолирован от реальной БД через mock_session.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, status

from services.tasks_repository import TaskRepository
from schemas.task import STaskAdd, STaskPatch

pytestmark = pytest.mark.unit


# ============================================================
# add_one
# ============================================================

class TestAddOne:
    """Тесты для TaskRepository.add_one."""

    @pytest.mark.asyncio
    async def test_add_one_success(self, mock_session, sample_task_data):
        """
        Arrange: STaskAdd с данными, mock_session
        Act: TaskRepository.add_one(data, session=mock_session)
        Assert: задача создана, session.add/commit/refresh вызваны
        """
        # Настраиваем refresh, чтобы установить id
        async def refresh_side_effect(task):
            task.id = 1

        mock_session.refresh.side_effect = refresh_side_effect

        result = await TaskRepository.add_one(
            data=sample_task_data, session=mock_session
        )

        assert result.id == 1
        assert result.name == "Test Task"
        assert result.description == "Test Description"
        assert result.is_completed is False
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_one_sets_is_completed_default(self, mock_session):
        """
        Arrange: STaskAdd без is_completed
        Act: TaskRepository.add_one(data, session=mock_session)
        Assert: is_completed = False
        """
        data = STaskAdd(name="Task", description=None)

        async def refresh_side_effect(task):
            task.id = 2

        mock_session.refresh.side_effect = refresh_side_effect

        result = await TaskRepository.add_one(data=data, session=mock_session)

        assert result.is_completed is False

    @pytest.mark.asyncio
    async def test_add_one_with_completed_true(self, mock_session):
        """
        Arrange: STaskAdd с is_completed=True
        Act: TaskRepository.add_one(data, session=mock_session)
        Assert: is_completed = True
        """
        data = STaskAdd(name="Task", is_completed=True)

        async def refresh_side_effect(task):
            task.id = 3

        mock_session.refresh.side_effect = refresh_side_effect

        result = await TaskRepository.add_one(data=data, session=mock_session)

        assert result.is_completed is True


# ============================================================
# find_all
# ============================================================

class TestFindAll:
    """Тесты для TaskRepository.find_all."""

    @pytest.mark.asyncio
    async def test_find_all_returns_list(self, mock_session, sample_task_model):
        """
        Arrange: mock_session возвращает список с одной задачей
        Act: TaskRepository.find_all(session=mock_session)
        Assert: вернулся список с одним элементом
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_task_model]
        mock_session.execute.return_value = mock_result

        result = await TaskRepository.find_all(session=mock_session)

        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].name == "Test Task"

    @pytest.mark.asyncio
    async def test_find_all_empty(self, mock_session):
        """
        Arrange: mock_session возвращает пустой список
        Act: TaskRepository.find_all(session=mock_session)
        Assert: вернулся пустой список
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await TaskRepository.find_all(session=mock_session)

        assert result == []

    @pytest.mark.asyncio
    async def test_find_all_with_pagination(self, mock_session):
        """
        Arrange: mock_session, параметры skip=10, limit=5
        Act: TaskRepository.find_all(session=mock_session, skip=10, limit=5)
        Assert: в запросе есть OFFSET и LIMIT
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await TaskRepository.find_all(session=mock_session, skip=10, limit=5)

        # Проверяем, что execute был вызван с запросом, содержащим OFFSET и LIMIT
        call_args = mock_session.execute.call_args
        assert call_args is not None
        query_str = str(call_args[0][0])
        assert "OFFSET" in query_str.upper()
        assert "LIMIT" in query_str.upper()

    @pytest.mark.asyncio
    async def test_find_all_filter_completed(self, mock_session):
        """
        Arrange: mock_session, is_completed=True
        Act: TaskRepository.find_all(session=mock_session, is_completed=True)
        Assert: в запросе есть WHERE is_completed
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await TaskRepository.find_all(session=mock_session, is_completed=True)

        call_args = mock_session.execute.call_args
        assert call_args is not None
        query_str = str(call_args[0][0])
        assert "is_completed" in query_str

    @pytest.mark.asyncio
    async def test_find_all_filter_not_completed(self, mock_session):
        """
        Arrange: mock_session, is_completed=False
        Act: TaskRepository.find_all(session=mock_session, is_completed=False)
        Assert: в запросе есть WHERE is_completed = false
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await TaskRepository.find_all(session=mock_session, is_completed=False)

        call_args = mock_session.execute.call_args
        assert call_args is not None
        query_str = str(call_args[0][0])
        assert "is_completed" in query_str

    @pytest.mark.asyncio
    async def test_find_all_no_filter(self, mock_session):
        """
        Arrange: mock_session, is_completed=None
        Act: TaskRepository.find_all(session=mock_session, is_completed=None)
        Assert: в запросе НЕТ WHERE по is_completed
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await TaskRepository.find_all(session=mock_session, is_completed=None)

        call_args = mock_session.execute.call_args
        assert call_args is not None
        query_str = str(call_args[0][0])
        # Проверяем, что нет WHERE (только OFFSET/LIMIT)
        assert "WHERE" not in query_str.upper() or "is_completed" not in query_str


# ============================================================
# find_one_or_404
# ============================================================

class TestFindOneOr404:
    """Тесты для TaskRepository.find_one_or_404."""

    @pytest.mark.asyncio
    async def test_find_one_found(self, mock_session, sample_task_model):
        """
        Arrange: mock_session возвращает задачу
        Act: TaskRepository.find_one_or_404(1, session=mock_session)
        Assert: вернулась задача с id=1
        """
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_task_model
        mock_session.execute.return_value = mock_result

        result = await TaskRepository.find_one_or_404(1, session=mock_session)

        assert result.id == 1
        assert result.name == "Test Task"

    @pytest.mark.asyncio
    async def test_find_one_not_found(self, mock_session):
        """
        Arrange: mock_session возвращает None
        Act: TaskRepository.find_one_or_404(999, session=mock_session)
        Assert: HTTPException(404)
        """
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await TaskRepository.find_one_or_404(999, session=mock_session)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "999" in exc_info.value.detail


# ============================================================
# update_full
# ============================================================

class TestUpdateFull:
    """Тесты для TaskRepository.update_full."""

    @pytest.mark.asyncio
    async def test_update_full_success(self, mock_session, sample_task_model):
        """
        Arrange: существующая задача, новые данные
        Act: TaskRepository.update_full(1, data, session=mock_session)
        Assert: поля обновлены
        """
        # Мокаем find_one_or_404 через патч
        with patch.object(TaskRepository, 'find_one_or_404', return_value=sample_task_model):
            data = STaskPatch(
                name="Updated Name",
                description="Updated Desc",
                is_completed=True
            )

            async def refresh_side_effect(task):
                task.name = "Updated Name"
                task.description = "Updated Desc"
                task.is_completed = True

            mock_session.refresh.side_effect = refresh_side_effect

            result = await TaskRepository.update_full(
                1, data=data, session=mock_session
            )

            assert result.name == "Updated Name"
            assert result.description == "Updated Desc"
            assert result.is_completed is True
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_full_not_found(self, mock_session):
        """
        Arrange: задача не найдена
        Act: TaskRepository.update_full(999, data, session=mock_session)
        Assert: HTTPException(404)
        """
        with patch.object(
            TaskRepository, 'find_one_or_404',
            side_effect=HTTPException(status_code=404, detail="Task with id 999 not found")
        ):
            data = STaskPatch(name="Updated", description="Desc", is_completed=False)

            with pytest.raises(HTTPException) as exc_info:
                await TaskRepository.update_full(
                    999, data=data, session=mock_session
                )

            assert exc_info.value.status_code == 404


# ============================================================
# patch
# ============================================================

class TestPatch:
    """Тесты для TaskRepository.patch."""

    @pytest.mark.asyncio
    async def test_patch_is_completed_only(self, mock_session, sample_task_model):
        """
        Arrange: существующая задача, is_completed=True
        Act: TaskRepository.patch(1, data, session=mock_session)
        Assert: is_completed=True, name/description не изменились
        """
        with patch.object(TaskRepository, 'find_one_or_404', return_value=sample_task_model):
            data = STaskPatch(is_completed=True)

            async def refresh_side_effect(task):
                task.is_completed = True

            mock_session.refresh.side_effect = refresh_side_effect

            result = await TaskRepository.patch(
                1, data=data, session=mock_session
            )

            assert result.is_completed is True
            assert result.name == "Test Task"  # не изменилось
            assert result.description == "Test Description"  # не изменилось
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_patch_name_only(self, mock_session, sample_task_model):
        """
        Arrange: существующая задача, новый name
        Act: TaskRepository.patch(1, data, session=mock_session)
        Assert: name обновлён, остальные поля не изменились
        """
        with patch.object(TaskRepository, 'find_one_or_404', return_value=sample_task_model):
            data = STaskPatch(name="New Name")

            async def refresh_side_effect(task):
                task.name = "New Name"

            mock_session.refresh.side_effect = refresh_side_effect

            result = await TaskRepository.patch(
                1, data=data, session=mock_session
            )

            assert result.name == "New Name"
            assert result.description == "Test Description"  # не изменилось
            assert result.is_completed is False  # не изменилось

    @pytest.mark.asyncio
    async def test_patch_no_changes(self, mock_session, sample_task_model):
        """
        Arrange: существующая задача, пустой STaskPatch
        Act: TaskRepository.patch(1, data, session=mock_session)
        Assert: задача не изменилась, commit вызван
        """
        with patch.object(TaskRepository, 'find_one_or_404', return_value=sample_task_model):
            data = STaskPatch()  # все поля None

            result = await TaskRepository.patch(
                1, data=data, session=mock_session
            )

            assert result.name == "Test Task"
            assert result.description == "Test Description"
            assert result.is_completed is False
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_patch_not_found(self, mock_session):
        """
        Arrange: задача не найдена
        Act: TaskRepository.patch(999, data, session=mock_session)
        Assert: HTTPException(404)
        """
        with patch.object(
            TaskRepository, 'find_one_or_404',
            side_effect=HTTPException(status_code=404, detail="Task with id 999 not found")
        ):
            data = STaskPatch(name="Updated")

            with pytest.raises(HTTPException) as exc_info:
                await TaskRepository.patch(999, data=data, session=mock_session)

            assert exc_info.value.status_code == 404


# ============================================================
# delete
# ============================================================

class TestDelete:
    """Тесты для TaskRepository.delete."""

    @pytest.mark.asyncio
    async def test_delete_success(self, mock_session, sample_task_model):
        """
        Arrange: существующая задача
        Act: TaskRepository.delete(1, session=mock_session)
        Assert: session.delete и session.commit вызваны
        """
        with patch.object(TaskRepository, 'find_one_or_404', return_value=sample_task_model):
            await TaskRepository.delete(1, session=mock_session)

            mock_session.delete.assert_called_once_with(sample_task_model)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, mock_session):
        """
        Arrange: задача не найдена
        Act: TaskRepository.delete(999, session=mock_session)
        Assert: HTTPException(404)
        """
        with patch.object(
            TaskRepository, 'find_one_or_404',
            side_effect=HTTPException(status_code=404, detail="Task with id 999 not found")
        ):
            with pytest.raises(HTTPException) as exc_info:
                await TaskRepository.delete(999, session=mock_session)

            assert exc_info.value.status_code == 404