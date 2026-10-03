"""
Unit-тесты для UserRepository (services/users_repository.py).

Все тесты следуют паттерну Arrange-Act-Assert.
Репозиторий изолирован от реальной БД через mock_session.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, status

from services.users_repository import UserRepository
from schemas.user import SUserAdd, SUserPatch

pytestmark = pytest.mark.unit


# ============================================================
# add_one
# ============================================================

class TestAddOne:
    """Тесты для UserRepository.add_one."""

    @pytest.mark.asyncio
    async def test_add_one_success(self, mock_session):
        """
        Arrange: SUserAdd с данными, mock_session (email свободен)
        Act: UserRepository.add_one(data, session=mock_session)
        Assert: пользователь создан, add/commit/refresh вызваны
        """
        data = SUserAdd(name="Test User", email="test@example.com")

        # find_by_email вернёт None (email свободен)
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        async def refresh_side_effect(user):
            user.id = 1

        mock_session.refresh.side_effect = refresh_side_effect

        result = await UserRepository.add_one(data=data, session=mock_session)

        assert result.id == 1
        assert result.name == "Test User"
        assert result.email == "test@example.com"
        assert result.is_active is True  # значение по умолчанию
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_one_existing_email_raises_400(self, mock_session, sample_user_model):
        """
        Arrange: пользователь с таким email уже существует
        Act: UserRepository.add_one(data, session=mock_session)
        Assert: HTTPException(400)
        """
        data = SUserAdd(name="Another", email="test@example.com")
        mock_session.execute.return_value.scalar_one_or_none.return_value = sample_user_model

        with pytest.raises(HTTPException) as exc_info:
            await UserRepository.add_one(data=data, session=mock_session)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "test@example.com" in exc_info.value.detail
        mock_session.add.assert_not_called()


# ============================================================
# find_all
# ============================================================

class TestFindAll:
    """Тесты для UserRepository.find_all."""

    @pytest.mark.asyncio
    async def test_find_all_returns_list(self, mock_session, sample_user_model):
        """
        Arrange: mock_session возвращает список с одним пользователем
        Act: UserRepository.find_all(session=mock_session)
        Assert: вернулся список с одним элементом
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = [sample_user_model]
        mock_session.execute.return_value = mock_result

        result = await UserRepository.find_all(session=mock_session)

        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].name == "Test User"

    @pytest.mark.asyncio
    async def test_find_all_empty(self, mock_session):
        """
        Arrange: mock_session возвращает пустой список
        Act: UserRepository.find_all(session=mock_session)
        Assert: вернулся пустой список
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await UserRepository.find_all(session=mock_session)

        assert result == []

    @pytest.mark.asyncio
    async def test_find_all_with_pagination(self, mock_session):
        """
        Arrange: mock_session, параметры skip=10, limit=5
        Act: UserRepository.find_all(session=mock_session, skip=10, limit=5)
        Assert: в запросе есть OFFSET и LIMIT
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await UserRepository.find_all(session=mock_session, skip=10, limit=5)

        call_args = mock_session.execute.call_args
        assert call_args is not None
        query_str = str(call_args[0][0])
        assert "OFFSET" in query_str.upper()
        assert "LIMIT" in query_str.upper()

    @pytest.mark.asyncio
    async def test_find_all_has_completed_tasks_true_joins_tasks(self, mock_session):
        """
        Arrange: mock_session, has_completed_tasks=True
        Act: UserRepository.find_all(session=mock_session, has_completed_tasks=True)
        Assert: в запросе есть JOIN с tasks и фильтр is_completed
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await UserRepository.find_all(session=mock_session, has_completed_tasks=True)

        call_args = mock_session.execute.call_args
        assert call_args is not None
        query_str = str(call_args[0][0]).upper()
        assert "JOIN" in query_str
        assert "IS_COMPLETED" in query_str
        assert "DISTINCT" in query_str

    @pytest.mark.asyncio
    async def test_find_all_has_completed_tasks_false_joins_tasks(self, mock_session):
        """
        Arrange: mock_session, has_completed_tasks=False
        Act: UserRepository.find_all(session=mock_session, has_completed_tasks=False)
        Assert: в запросе есть JOIN с tasks и фильтр is_completed
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await UserRepository.find_all(session=mock_session, has_completed_tasks=False)

        call_args = mock_session.execute.call_args
        assert call_args is not None
        query_str = str(call_args[0][0]).upper()
        assert "JOIN" in query_str
        assert "IS_COMPLETED" in query_str

    @pytest.mark.asyncio
    async def test_find_all_no_filter(self, mock_session):
        """
        Arrange: mock_session, фильтр не передан
        Act: UserRepository.find_all(session=mock_session)
        Assert: в запросе НЕТ JOIN и фильтра по is_completed
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await UserRepository.find_all(session=mock_session)

        call_args = mock_session.execute.call_args
        assert call_args is not None
        query_str = str(call_args[0][0]).upper()
        assert "JOIN" not in query_str
        assert "IS_COMPLETED" not in query_str


# ============================================================
# find_one_or_404
# ============================================================

class TestFindOneOr404:
    """Тесты для UserRepository.find_one_or_404."""

    @pytest.mark.asyncio
    async def test_find_one_found(self, mock_session, sample_user_model):
        """
        Arrange: session.get возвращает пользователя
        Act: UserRepository.find_one_or_404(1, session=mock_session)
        Assert: вернулся пользователь с id=1
        """
        mock_session.get.return_value = sample_user_model

        result = await UserRepository.find_one_or_404(1, session=mock_session)

        assert result.id == 1
        assert result.name == "Test User"

    @pytest.mark.asyncio
    async def test_find_one_not_found(self, mock_session):
        """
        Arrange: session.get возвращает None
        Act: UserRepository.find_one_or_404(999, session=mock_session)
        Assert: HTTPException(404)
        """
        mock_session.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await UserRepository.find_one_or_404(999, session=mock_session)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "999" in exc_info.value.detail


# ============================================================
# find_by_email
# ============================================================

class TestFindByEmail:
    """Тесты для UserRepository.find_by_email."""

    @pytest.mark.asyncio
    async def test_find_by_email_found(self, mock_session, sample_user_model):
        """
        Arrange: execute возвращает пользователя
        Act: UserRepository.find_by_email("test@example.com", session=mock_session)
        Assert: вернулся пользователь
        """
        mock_session.execute.return_value.scalar_one_or_none.return_value = sample_user_model

        result = await UserRepository.find_by_email("test@example.com", session=mock_session)

        assert result is sample_user_model

    @pytest.mark.asyncio
    async def test_find_by_email_not_found(self, mock_session):
        """
        Arrange: execute возвращает None
        Act: UserRepository.find_by_email("nobody@example.com", session=mock_session)
        Assert: вернулся None
        """
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        result = await UserRepository.find_by_email("nobody@example.com", session=mock_session)

        assert result is None


# ============================================================
# find_one_with_tasks
# ============================================================

class TestFindOneWithTasks:
    """Тесты для UserRepository.find_one_with_tasks."""

    @pytest.mark.asyncio
    async def test_find_one_with_tasks_success(self, mock_session, sample_user_model):
        """
        Arrange: execute возвращает пользователя
        Act: UserRepository.find_one_with_tasks(1, session=mock_session)
        Assert: вернулся пользователь, execute вызывался (запрос с selectinload)
        """
        mock_session.execute.return_value.scalar_one_or_none.return_value = sample_user_model

        result = await UserRepository.find_one_with_tasks(1, session=mock_session)

        assert result is sample_user_model
        mock_session.execute.assert_awaited()

    @pytest.mark.asyncio
    async def test_find_one_with_tasks_not_found(self, mock_session):
        """
        Arrange: execute возвращает None
        Act: UserRepository.find_one_with_tasks(999, session=mock_session)
        Assert: HTTPException(404)
        """
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await UserRepository.find_one_with_tasks(999, session=mock_session)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ============================================================
# update_full
# ============================================================

class TestUpdateFull:
    """Тесты для UserRepository.update_full."""

    @pytest.mark.asyncio
    async def test_update_full_success(self, mock_session, sample_user_model):
        """
        Arrange: существующий пользователь, новые данные
        Act: UserRepository.update_full(1, data, session=mock_session)
        Assert: поля обновлены, commit вызван
        """
        with patch.object(UserRepository, 'find_one_or_404', return_value=sample_user_model):
            data = SUserAdd(name="Updated User", email="updated@example.com", is_active=False)

            async def refresh_side_effect(user):
                user.name = "Updated User"
                user.email = "updated@example.com"
                user.is_active = False

            mock_session.refresh.side_effect = refresh_side_effect

            result = await UserRepository.update_full(
                1, data=data, session=mock_session
            )

            assert result.name == "Updated User"
            assert result.email == "updated@example.com"
            assert result.is_active is False
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_full_not_found(self, mock_session):
        """
        Arrange: пользователь не найден
        Act: UserRepository.update_full(999, data, session=mock_session)
        Assert: HTTPException(404)
        """
        with patch.object(
            UserRepository, 'find_one_or_404',
            side_effect=HTTPException(status_code=404, detail="Пользователь с id 999 Не найден")
        ):
            data = SUserAdd(name="Updated", email="updated@example.com")

            with pytest.raises(HTTPException) as exc_info:
                await UserRepository.update_full(
                    999, data=data, session=mock_session
                )

            assert exc_info.value.status_code == 404


# ============================================================
# patch
# ============================================================

class TestPatch:
    """Тесты для UserRepository.patch."""

    @pytest.mark.asyncio
    async def test_patch_name_only(self, mock_session, sample_user_model):
        """
        Arrange: существующий пользователь, новый name
        Act: UserRepository.patch(1, data, session=mock_session)
        Assert: name обновлён, остальные поля не изменились
        """
        with patch.object(UserRepository, 'find_one_or_404', return_value=sample_user_model):
            data = SUserPatch(name="New Name")

            async def refresh_side_effect(user):
                user.name = "New Name"

            mock_session.refresh.side_effect = refresh_side_effect

            result = await UserRepository.patch(
                1, data=data, session=mock_session
            )

            assert result.name == "New Name"
            assert result.email == "test@example.com"  # не изменилось
            assert result.is_active is True  # не изменилось
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_patch_is_active_false(self, mock_session, sample_user_model):
        """
        Arrange: существующий пользователь, is_active=False
        Act: UserRepository.patch(1, data, session=mock_session)
        Assert: is_active=False, name не изменился
        """
        with patch.object(UserRepository, 'find_one_or_404', return_value=sample_user_model):
            data = SUserPatch(is_active=False)

            result = await UserRepository.patch(
                1, data=data, session=mock_session
            )

            assert result.is_active is False
            assert result.name == "Test User"  # не изменилось
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_patch_no_changes(self, mock_session, sample_user_model):
        """
        Arrange: существующий пользователь, пустой SUserPatch
        Act: UserRepository.patch(1, data, session=mock_session)
        Assert: пользователь не изменился, commit вызван
        """
        with patch.object(UserRepository, 'find_one_or_404', return_value=sample_user_model):
            data = SUserPatch()  # все поля None

            result = await UserRepository.patch(
                1, data=data, session=mock_session
            )

            assert result.name == "Test User"
            assert result.email == "test@example.com"
            assert result.is_active is True
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_patch_not_found(self, mock_session):
        """
        Arrange: пользователь не найден
        Act: UserRepository.patch(999, data, session=mock_session)
        Assert: HTTPException(404)
        """
        with patch.object(
            UserRepository, 'find_one_or_404',
            side_effect=HTTPException(status_code=404, detail="Пользователь с id 999 Не найден")
        ):
            data = SUserPatch(name="Updated")

            with pytest.raises(HTTPException) as exc_info:
                await UserRepository.patch(999, data=data, session=mock_session)

            assert exc_info.value.status_code == 404


# ============================================================
# delete
# ============================================================

class TestDelete:
    """Тесты для UserRepository.delete."""

    @pytest.mark.asyncio
    async def test_delete_success(self, mock_session, sample_user_model):
        """
        Arrange: существующий пользователь
        Act: UserRepository.delete(1, session=mock_session)
        Assert: session.delete и session.commit вызваны
        """
        with patch.object(UserRepository, 'find_one_or_404', return_value=sample_user_model):
            await UserRepository.delete(1, session=mock_session)

            mock_session.delete.assert_called_once_with(sample_user_model)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, mock_session):
        """
        Arrange: пользователь не найден
        Act: UserRepository.delete(999, session=mock_session)
        Assert: HTTPException(404)
        """
        with patch.object(
            UserRepository, 'find_one_or_404',
            side_effect=HTTPException(status_code=404, detail="Пользователь с id 999 Не найден")
        ):
            with pytest.raises(HTTPException) as exc_info:
                await UserRepository.delete(999, session=mock_session)

            assert exc_info.value.status_code == 404