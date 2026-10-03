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
        assert result.title == "Test Task"
        assert result.description == "Test Description"
        assert result.priority == 3
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
        data = STaskAdd(title="Task", description=None, priority=2)

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
        data = STaskAdd(title="Task", priority=1, is_completed=True)

        async def refresh_side_effect(task):
            task.id = 3

        mock_session.refresh.side_effect = refresh_side_effect

        result = await TaskRepository.add_one(data=data, session=mock_session)

        assert result.is_completed is True

    @pytest.mark.asyncio
    async def test_add_one_with_nonexistent_user_raises_404(self, mock_session):
        """
        Arrange: user_id не существует (session.get вернёт None)
        Act: TaskRepository.add_one(data, session=mock_session)
        Assert: HTTPException(404)
        """
        data = STaskAdd(title="Task", priority=3, user_id=999)
        mock_session.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await TaskRepository.add_one(data=data, session=mock_session)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "999" in exc_info.value.detail


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
        assert result[0].title == "Test Task"

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
        Assert: в запросе есть WHERE is_completed
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
    async def test_find_all_filter_by_user(self, mock_session):
        """
        Arrange: mock_session, user_id=5
        Act: TaskRepository.find_all(session=mock_session, user_id=5)
        Assert: в запросе есть WHERE по user_id
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await TaskRepository.find_all(session=mock_session, user_id=5)

        call_args = mock_session.execute.call_args
        assert call_args is not None
        query_str = str(call_args[0][0])
        assert "user_id" in query_str

    @pytest.mark.asyncio
    async def test_find_all_no_filter(self, mock_session):
        """
        Arrange: mock_session, фильтры None
        Act: TaskRepository.find_all(session=mock_session)
        Assert: в запросе НЕТ WHERE по is_completed/user_id
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await TaskRepository.find_all(session=mock_session)

        call_args = mock_session.execute.call_args
        assert call_args is not None
        query_str = str(call_args[0][0])
        # Проверяем, что нет фильтров (только OFFSET/LIMIT)
        assert "WHERE" not in query_str.upper() or (
            "is_completed" not in query_str and "user_id" not in query_str
        )


# ============================================================
# find_one_or_404
# ============================================================

class TestFindOneOr404:
    """Тесты для TaskRepository.find_one_or_404."""

    @pytest.mark.asyncio
    async def test_find_one_found(self, mock_session, sample_task_model):
        """
        Arrange: session.get возвращает задачу
        Act: TaskRepository.find_one_or_404(1, session=mock_session)
        Assert: вернулась задача с id=1
        """
        mock_session.get.return_value = sample_task_model

        result = await TaskRepository.find_one_or_404(1, session=mock_session)

        assert result.id == 1
        assert result.title == "Test Task"

    @pytest.mark.asyncio
    async def test_find_one_not_found(self, mock_session):
        """
        Arrange: session.get возвращает None
        Act: TaskRepository.find_one_or_404(999, session=mock_session)
        Assert: HTTPException(404)
        """
        mock_session.get.return_value = None

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
        Assert: поля обновлены, commit вызван
        """
        # Мокаем find_one_or_404 через патч
        with patch.object(TaskRepository, 'find_one_or_404', return_value=sample_task_model):
            data = STaskAdd(
                title="Updated Title",
                description="Updated Desc",
                is_completed=True,
                priority=2,
            )

            async def refresh_side_effect(task):
                task.title = "Updated Title"
                task.description = "Updated Desc"
                task.is_completed = True
                task.priority = 2

            mock_session.refresh.side_effect = refresh_side_effect

            result = await TaskRepository.update_full(
                1, data=data, session=mock_session
            )

            assert result.title == "Updated Title"
            assert result.description == "Updated Desc"
            assert result.is_completed is True
            assert result.priority == 2
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_full_assigns_new_user(self, mock_session, sample_task_model):
        """
        Arrange: существующая задача, новый исполнитель user_id=5
        Act: TaskRepository.update_full(1, data, session=mock_session)
        Assert: session.get(UserModel, 5) вызывался, user_id обновлён
        """
        mock_session.get.return_value = MagicMock()  # пользователь существует

        with patch.object(TaskRepository, 'find_one_or_404', return_value=sample_task_model):
            data = STaskAdd(title="Updated", priority=3, user_id=5)

            async def refresh_side_effect(task):
                task.title = "Updated"

            mock_session.refresh.side_effect = refresh_side_effect

            result = await TaskRepository.update_full(
                1, data=data, session=mock_session
            )

            assert result.user_id == 5
            mock_session.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_full_nonexistent_user_raises_404(self, mock_session, sample_task_model):
        """
        Arrange: новый исполнитель не существует (session.get → None)
        Act: TaskRepository.update_full(1, data, session=mock_session)
        Assert: HTTPException(404)
        """
        mock_session.get.return_value = None

        with patch.object(TaskRepository, 'find_one_or_404', return_value=sample_task_model):
            data = STaskAdd(title="Updated", priority=3, user_id=999)

            with pytest.raises(HTTPException) as exc_info:
                await TaskRepository.update_full(
                    1, data=data, session=mock_session
                )

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_full_not_found(self, mock_session):
        """
        Arrange: задача не найдена
        Act: TaskRepository.update_full(999, data, session=mock_session)
        Assert: HTTPException(404)
        """
        with patch.object(
            TaskRepository, 'find_one_or_404',
            side_effect=HTTPException(status_code=404, detail="Задача с id 999 не найдена")
        ):
            data = STaskAdd(title="Updated", priority=3)

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
        Assert: is_completed=True, title/description не изменились
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
            assert result.title == "Test Task"  # не изменилось
            assert result.description == "Test Description"  # не изменилось
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_patch_title_only(self, mock_session, sample_task_model):
        """
        Arrange: существующая задача, новый title
        Act: TaskRepository.patch(1, data, session=mock_session)
        Assert: title обновлён, остальные поля не изменились
        """
        with patch.object(TaskRepository, 'find_one_or_404', return_value=sample_task_model):
            data = STaskPatch(title="New Title")

            async def refresh_side_effect(task):
                task.title = "New Title"

            mock_session.refresh.side_effect = refresh_side_effect

            result = await TaskRepository.patch(
                1, data=data, session=mock_session
            )

            assert result.title == "New Title"
            assert result.description == "Test Description"  # не изменилось
            assert result.is_completed is False  # не изменилось

    @pytest.mark.asyncio
    async def test_patch_assigns_new_user(self, mock_session, sample_task_model):
        """
        Arrange: задача существует, назначаем исполнителя user_id=5
        Act: TaskRepository.patch(1, data, session=mock_session)
        Assert: user_id обновлён, session.get вызывался
        """
        mock_session.get.return_value = MagicMock()  # пользователь существует

        with patch.object(TaskRepository, 'find_one_or_404', return_value=sample_task_model):
            data = STaskPatch(user_id=5)

            result = await TaskRepository.patch(
                1, data=data, session=mock_session
            )

            assert result.user_id == 5
            mock_session.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_patch_nonexistent_user_raises_404(self, mock_session, sample_task_model):
        """
        Arrange: назначаем несуществующего исполнителя
        Act: TaskRepository.patch(1, data, session=mock_session)
        Assert: HTTPException(404)
        """
        mock_session.get.return_value = None

        with patch.object(TaskRepository, 'find_one_or_404', return_value=sample_task_model):
            data = STaskPatch(user_id=999)

            with pytest.raises(HTTPException) as exc_info:
                await TaskRepository.patch(
                    1, data=data, session=mock_session
                )

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_patch_null_for_required_field_raises_422(self, mock_session, sample_task_model):
        """
        Arrange: PATCH с явным null для обязательного поля title
        Act: TaskRepository.patch(1, data, session=mock_session)
        Assert: HTTPException(422)
        """
        with patch.object(TaskRepository, 'find_one_or_404', return_value=sample_task_model):
            data = STaskPatch(title=None)  # title NOT NULL в БД

            with pytest.raises(HTTPException) as exc_info:
                await TaskRepository.patch(
                    1, data=data, session=mock_session
                )

            assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
            assert "title" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_patch_unassign_user_ok(self, mock_session, sample_task_model):
        """
        Arrange: PATCH с user_id=None (отвязка исполнителя — легитимно)
        Act: TaskRepository.patch(1, data, session=mock_session)
        Assert: ошибки нет, user_id стал None
        """
        sample_task_model.user_id = 5  # была назначена

        with patch.object(TaskRepository, 'find_one_or_404', return_value=sample_task_model):
            data = STaskPatch(user_id=None)

            result = await TaskRepository.patch(
                1, data=data, session=mock_session
            )

            assert result.user_id is None
            mock_session.commit.assert_called_once()

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

            assert result.title == "Test Task"
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
            side_effect=HTTPException(status_code=404, detail="Задача с id 999 не найдена")
        ):
            data = STaskPatch(title="Updated")

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
            side_effect=HTTPException(status_code=404, detail="Задача с id 999 не найдена")
        ):
            with pytest.raises(HTTPException) as exc_info:
                await TaskRepository.delete(999, session=mock_session)

            assert exc_info.value.status_code == 404


# ============================================================
# find_unassigned
# ============================================================

class TestFindUnassigned:
    """Тесты для TaskRepository.find_unassigned."""

    @pytest.mark.asyncio
    async def test_find_unassigned_filters_user_id_is_null(self, mock_session):
        """
        Arrange: mock_session, пустой результат
        Act: TaskRepository.find_unassigned(session=mock_session)
        Assert: в запросе есть IS NULL по user_id
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await TaskRepository.find_unassigned(session=mock_session)

        call_args = mock_session.execute.call_args
        assert call_args is not None
        query_str = str(call_args[0][0])
        assert "IS NULL" in query_str.upper()
        assert "user_id" in query_str

    @pytest.mark.asyncio
    async def test_find_unassigned_returns_tasks(self, mock_session, sample_task_model):
        """
        Arrange: mock_session возвращает одну задачу без исполнителя
        Act: TaskRepository.find_unassigned(session=mock_session)
        Assert: вернулся список с одной задачей
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_task_model]
        mock_session.execute.return_value = mock_result

        result = await TaskRepository.find_unassigned(session=mock_session)

        assert len(result) == 1
        assert result[0].id == 1