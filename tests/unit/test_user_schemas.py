"""
Unit-тесты для Pydantic-схем пользователей (schemas/user.py).

Проверяем:
- Валидацию полей (min_length, max_length, EmailStr)
- Значения по умолчанию
- Запрет лишних полей (extra="forbid") для SUserPatch
- Преобразование из ORM-модели (from_attributes), в т.ч. со списком задач
"""
import pytest
from pydantic import ValidationError
from schemas.user import SUserAdd, SUser, SUserPatch, SUserWithTasks

pytestmark = pytest.mark.unit


# ============================================================
# SUserAdd — схема для создания пользователя (POST)
# ============================================================

class TestSUserAdd:
    """Тесты для схемы создания пользователя."""

    def test_valid_full_data(self):
        """
        Arrange: полные валидные данные
        Act: создаём SUserAdd
        Assert: все поля установлены корректно
        """
        data = {"name": "Ivan", "email": "ivan@example.com", "is_active": False}
        user = SUserAdd(**data)
        assert user.name == "Ivan"
        assert user.email == "ivan@example.com"
        assert user.is_active is False

    def test_default_is_active(self):
        """
        Arrange: без is_active
        Act: создаём SUserAdd
        Assert: is_active = True (значение по умолчанию)
        """
        user = SUserAdd(name="Ivan", email="ivan@example.com")
        assert user.is_active is True

    def test_invalid_email(self):
        """
        Arrange: некорректный email
        Act: создаём SUserAdd
        Assert: ValidationError (EmailStr)
        """
        with pytest.raises(ValidationError):
            SUserAdd(name="Ivan", email="not-an-email")

    def test_name_too_short(self):
        """
        Arrange: name длиной 0 символов (min_length=1)
        Act: создаём SUserAdd
        Assert: ValidationError
        """
        with pytest.raises(ValidationError):
            SUserAdd(name="", email="ivan@example.com")

    def test_name_too_long(self):
        """
        Arrange: name длиной 101 символ (max_length=100)
        Act: создаём SUserAdd
        Assert: ValidationError с ошибкой о max_length
        """
        with pytest.raises(ValidationError) as exc_info:
            SUserAdd(name="A" * 101, email="ivan@example.com")
        errors = exc_info.value.errors()
        assert any("max_length" in str(err) for err in errors)

    def test_extra_field_ignored(self):
        """
        Arrange: передаём лишнее поле
        Act: создаём SUserAdd
        Assert: поле unknown_field игнорируется (extra=ignore у BaseModel)
        """
        user = SUserAdd(name="Ivan", email="ivan@example.com", unknown_field="value")
        assert user.name == "Ivan"


# ============================================================
# SUserPatch — схема для частичного обновления (PATCH)
# ============================================================

class TestSUserPatch:
    """Тесты для схемы частичного обновления пользователя."""

    def test_empty_patch(self):
        """
        Arrange: пустой словарь
        Act: создаём SUserPatch
        Assert: все поля None
        """
        patch = SUserPatch()
        assert patch.name is None
        assert patch.email is None
        assert patch.is_active is None

    def test_partial_name_only(self):
        """
        Arrange: только name
        Act: создаём SUserPatch
        Assert: name установлен, остальные None
        """
        patch = SUserPatch(name="New Name")
        assert patch.name == "New Name"
        assert patch.email is None
        assert patch.is_active is None

    def test_partial_is_active_only(self):
        """
        Arrange: только is_active
        Act: создаём SUserPatch
        Assert: is_active установлен, остальные None
        """
        patch = SUserPatch(is_active=False)
        assert patch.is_active is False
        assert patch.name is None

    def test_extra_field_forbidden(self):
        """
        Arrange: передаём лишнее поле
        Act: создаём SUserPatch
        Assert: ValidationError (extra="forbid")
        """
        with pytest.raises(ValidationError) as exc_info:
            SUserPatch(name="Task", extra_field="value")
        errors = exc_info.value.errors()
        assert any("extra" in str(err).lower() for err in errors)


# ============================================================
# SUser — схема для ответа API (GET, PUT, PATCH)
# ============================================================

class TestSUser:
    """Тесты для схемы ответа API."""

    def test_from_attributes(self):
        """
        Arrange: ORM-модель UserModel
        Act: SUser.model_validate(user_model)
        Assert: все поля совпадают
        """
        from models.users import UserModel
        user_model = UserModel()
        user_model.id = 1
        user_model.name = "Ivan"
        user_model.email = "ivan@example.com"
        user_model.is_active = True

        user = SUser.model_validate(user_model)
        assert user.id == 1
        assert user.name == "Ivan"
        assert user.email == "ivan@example.com"
        assert user.is_active is True


# ============================================================
# SUserWithTasks — пользователь со списком задач
# ============================================================

class TestSUserWithTasks:
    """Тесты для схемы пользователя со списком задач."""

    def _make_user_with_tasks(self):
        """Вспомогательный метод: UserModel с одной задачей."""
        from models.users import UserModel
        from models.tasks import TaskModel

        task = TaskModel()
        task.id = 10
        task.title = "My Task"
        task.description = "Desc"
        task.is_completed = False
        task.priority = 2
        task.user_id = 1

        user = UserModel()
        user.id = 1
        user.name = "Ivan"
        user.email = "ivan@example.com"
        user.is_active = True
        user.tasks = [task]
        return user

    def test_from_attributes_with_tasks(self):
        """
        Arrange: UserModel с одной задачей
        Act: SUserWithTasks.model_validate(user_model)
        Assert: поля пользователя + список задач корректны
        """
        user_model = self._make_user_with_tasks()

        user = SUserWithTasks.model_validate(user_model)
        assert user.id == 1
        assert user.name == "Ivan"
        assert len(user.tasks) == 1
        assert user.tasks[0].id == 10
        assert user.tasks[0].title == "My Task"
        assert user.tasks[0].priority == 2

    def test_from_attributes_no_tasks(self):
        """
        Arrange: UserModel без задач
        Act: SUserWithTasks.model_validate(user_model)
        Assert: tasks = []
        """
        from models.users import UserModel
        user_model = UserModel()
        user_model.id = 2
        user_model.name = "Petr"
        user_model.email = "petr@example.com"
        user_model.is_active = True
        user_model.tasks = []

        user = SUserWithTasks.model_validate(user_model)
        assert user.tasks == []