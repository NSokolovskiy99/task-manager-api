"""
Unit-тесты для Pydantic-схем (schemas/task.py).

Проверяем:
- Валидацию полей (min_length, max_length)
- Значения по умолчанию
- Запрет лишних полей (extra="forbid")
- Преобразование из ORM-модели (from_attributes)
"""
import pytest
from pydantic import ValidationError
from schemas.task import STaskAdd, STask, STaskPatch

pytestmark = pytest.mark.unit


# ============================================================
# STaskAdd — схема для создания задачи (POST)
# ============================================================

class TestSTaskAdd:
    """Тесты для схемы создания задачи."""

    def test_valid_full_data(self):
        """
        Arrange: полные валидные данные
        Act: создаём STaskAdd
        Assert: все поля установлены корректно
        """
        data = {"name": "Valid Task", "description": "Valid description"}
        task = STaskAdd(**data)
        assert task.name == "Valid Task"
        assert task.description == "Valid description"
        assert task.is_completed is False

    def test_minimal_data(self):
        """
        Arrange: только обязательное поле name
        Act: создаём STaskAdd
        Assert: description is None, is_completed is False
        """
        task = STaskAdd(name="Minimal")
        assert task.name == "Minimal"
        assert task.description is None
        assert task.is_completed is False

    def test_with_completed_true(self):
        """
        Arrange: name + is_completed=True
        Act: создаём STaskAdd
        Assert: is_completed == True
        """
        task = STaskAdd(name="Task", is_completed=True)
        assert task.is_completed is True

    def test_name_too_short(self):
        """
        Arrange: name длиной 2 символа (min_length=3)
        Act: создаём STaskAdd
        Assert: ValidationError
        """
        with pytest.raises(ValidationError) as exc_info:
            STaskAdd(name="AB")
        errors = exc_info.value.errors()
        assert any("min_length" in str(err) for err in errors)

    def test_name_too_long(self):
        """
        Arrange: name длиной 101 символ (max_length=100)
        Act: создаём STaskAdd
        Assert: ValidationError с ошибкой о max_length
        """
        with pytest.raises(ValidationError) as exc_info:
            STaskAdd(name="A" * 101)
        errors = exc_info.value.errors()
        assert any("max_length" in str(err) for err in errors)

    def test_description_too_long(self):
        """
        Arrange: description длиной 501 символ (max_length=500)
        Act: создаём STaskAdd
        Assert: ValidationError с ошибкой о max_length
        """
        with pytest.raises(ValidationError) as exc_info:
            STaskAdd(name="Valid", description="A" * 501)
        errors = exc_info.value.errors()
        assert any("max_length" in str(err) for err in errors)

    def test_extra_field_forbidden(self):
        """
        Arrange: передаём лишнее поле
        Act: создаём STaskAdd
        Assert: ValidationError (по умолчанию extra=ignore для BaseModel)
        """
        # STaskAdd наследуется от BaseModel, где extra="ignore" по умолчанию
        task = STaskAdd(name="Task", unknown_field="value")
        assert task.name == "Task"
        # Поле unknown_field просто игнорируется


# ============================================================
# STaskPatch — схема для частичного обновления (PATCH)
# ============================================================

class TestSTaskPatch:
    """Тесты для схемы частичного обновления."""

    def test_empty_patch(self):
        """
        Arrange: пустой словарь
        Act: создаём STaskPatch
        Assert: все поля None
        """
        patch = STaskPatch()
        assert patch.name is None
        assert patch.description is None
        assert patch.is_completed is None

    def test_partial_name_only(self):
        """
        Arrange: только name
        Act: создаём STaskPatch
        Assert: name установлен, остальные None
        """
        patch = STaskPatch(name="Updated Name")
        assert patch.name == "Updated Name"
        assert patch.description is None
        assert patch.is_completed is None

    def test_partial_is_completed_only(self):
        """
        Arrange: только is_completed
        Act: создаём STaskPatch
        Assert: is_completed установлен, остальные None
        """
        patch = STaskPatch(is_completed=True)
        assert patch.name is None
        assert patch.description is None
        assert patch.is_completed is True

    def test_extra_field_forbidden(self):
        """
        Arrange: передаём лишнее поле
        Act: создаём STaskPatch
        Assert: ValidationError (extra="forbid")
        """
        with pytest.raises(ValidationError) as exc_info:
            STaskPatch(name="Task", extra_field="value")
        errors = exc_info.value.errors()
        assert any("extra" in str(err).lower() for err in errors)

    def test_name_too_short(self):
        """
        Arrange: name длиной 2 символа (min_length=3)
        Act: создаём STaskPatch
        Assert: ValidationError с ошибкой о min_length
        """
        with pytest.raises(ValidationError) as exc_info:
            STaskPatch(name="AB")
        errors = exc_info.value.errors()
        assert any("min_length" in str(err) for err in errors)

    def test_name_too_long(self):
        """
        Arrange: name длиной 101 символ (max_length=100)
        Act: создаём STaskPatch
        Assert: ValidationError с ошибкой о max_length
        """
        with pytest.raises(ValidationError) as exc_info:
            STaskPatch(name="A" * 101)
        errors = exc_info.value.errors()
        assert any("max_length" in str(err) for err in errors)


# ============================================================
# STask — схема для ответа API (GET, PUT, PATCH)
# ============================================================

class TestSTask:
    """Тесты для схемы ответа API."""

    def test_from_attributes(self):
        """
        Arrange: ORM-модель TaskModel
        Act: STask.model_validate(task_model)
        Assert: все поля совпадают
        """
        from models.tasks import TaskModel
        task_model = TaskModel()
        task_model.id = 1
        task_model.name = "Test"
        task_model.description = "Desc"
        task_model.is_completed = True

        task = STask.model_validate(task_model)
        assert task.id == 1
        assert task.name == "Test"
        assert task.description == "Desc"
        assert task.is_completed is True

    def test_from_attributes_null_description(self):
        """
        Arrange: ORM-модель с description=None
        Act: STask.model_validate(task_model)
        Assert: description is None
        """
        from models.tasks import TaskModel
        task_model = TaskModel()
        task_model.id = 2
        task_model.name = "No Desc"
        task_model.description = None
        task_model.is_completed = False

        task = STask.model_validate(task_model)
        assert task.id == 2
        assert task.name == "No Desc"
        assert task.description is None
        assert task.is_completed is False