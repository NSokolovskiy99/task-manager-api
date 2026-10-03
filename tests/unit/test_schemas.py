"""
Unit-тесты для Pydantic-схем задач (schemas/task.py).

Проверяем:
- Валидацию полей (min_length, max_length, ge, le)
- Значения по умолчанию
- Обязательность поля priority
- Запрет лишних полей (extra="forbid") для PATCH
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
        data = {"title": "Valid Task", "description": "Valid description", "priority": 3}
        task = STaskAdd(**data)
        assert task.title == "Valid Task"
        assert task.description == "Valid description"
        assert task.priority == 3
        assert task.is_completed is False
        assert task.user_id is None

    def test_minimal_data(self):
        """
        Arrange: только обязательные поля title и priority
        Act: создаём STaskAdd
        Assert: description is None, is_completed is False, user_id is None
        """
        task = STaskAdd(title="Minimal", priority=1)
        assert task.title == "Minimal"
        assert task.description is None
        assert task.is_completed is False
        assert task.user_id is None

    def test_with_completed_true(self):
        """
        Arrange: title + priority + is_completed=True
        Act: создаём STaskAdd
        Assert: is_completed == True
        """
        task = STaskAdd(title="Task", priority=2, is_completed=True)
        assert task.is_completed is True

    def test_priority_required(self):
        """
        Arrange: нет обязательного priority
        Act: создаём STaskAdd
        Assert: ValidationError (поле priority обязательно)
        """
        with pytest.raises(ValidationError):
            STaskAdd(title="No priority")

    def test_priority_below_range(self):
        """
        Arrange: priority=0 (ge=1)
        Act: создаём STaskAdd
        Assert: ValidationError
        """
        with pytest.raises(ValidationError):
            STaskAdd(title="Task", priority=0)

    def test_priority_above_range(self):
        """
        Arrange: priority=6 (le=5)
        Act: создаём STaskAdd
        Assert: ValidationError
        """
        with pytest.raises(ValidationError):
            STaskAdd(title="Task", priority=6)

    def test_title_too_short(self):
        """
        Arrange: title длиной 2 символа (min_length=3)
        Act: создаём STaskAdd
        Assert: ValidationError
        """
        with pytest.raises(ValidationError) as exc_info:
            STaskAdd(title="AB", priority=3)
        errors = exc_info.value.errors()
        assert any("min_length" in str(err) for err in errors)

    def test_title_too_long(self):
        """
        Arrange: title длиной 201 символ (max_length=200)
        Act: создаём STaskAdd
        Assert: ValidationError с ошибкой о max_length
        """
        with pytest.raises(ValidationError) as exc_info:
            STaskAdd(title="A" * 201, priority=3)
        errors = exc_info.value.errors()
        assert any("max_length" in str(err) for err in errors)

    def test_description_too_long(self):
        """
        Arrange: description длиной 501 символ (max_length=500)
        Act: создаём STaskAdd
        Assert: ValidationError с ошибкой о max_length
        """
        with pytest.raises(ValidationError) as exc_info:
            STaskAdd(title="Valid", description="A" * 501, priority=3)
        errors = exc_info.value.errors()
        assert any("max_length" in str(err) for err in errors)

    def test_extra_field_ignored(self):
        """
        Arrange: передаём лишнее поле
        Act: создаём STaskAdd
        Assert: поле unknown_field просто игнорируется (extra=ignore у BaseModel)
        """
        task = STaskAdd(title="Task", priority=3, unknown_field="value")
        assert task.title == "Task"


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
        assert patch.title is None
        assert patch.description is None
        assert patch.is_completed is None
        assert patch.priority is None
        assert patch.user_id is None

    def test_partial_title_only(self):
        """
        Arrange: только title
        Act: создаём STaskPatch
        Assert: title установлен, остальные None
        """
        patch = STaskPatch(title="Updated Title")
        assert patch.title == "Updated Title"
        assert patch.description is None
        assert patch.is_completed is None

    def test_partial_is_completed_only(self):
        """
        Arrange: только is_completed
        Act: создаём STaskPatch
        Assert: is_completed установлен, остальные None
        """
        patch = STaskPatch(is_completed=True)
        assert patch.title is None
        assert patch.description is None
        assert patch.is_completed is True

    def test_extra_field_forbidden(self):
        """
        Arrange: передаём лишнее поле
        Act: создаём STaskPatch
        Assert: ValidationError (extra="forbid")
        """
        with pytest.raises(ValidationError) as exc_info:
            STaskPatch(title="Task", extra_field="value")
        errors = exc_info.value.errors()
        assert any("extra" in str(err).lower() for err in errors)

    def test_title_too_short(self):
        """
        Arrange: title длиной 2 символа (min_length=3)
        Act: создаём STaskPatch
        Assert: ValidationError с ошибкой о min_length
        """
        with pytest.raises(ValidationError) as exc_info:
            STaskPatch(title="AB")
        errors = exc_info.value.errors()
        assert any("min_length" in str(err) for err in errors)

    def test_title_too_long(self):
        """
        Arrange: title длиной 201 символ (max_length=200)
        Act: создаём STaskPatch
        Assert: ValidationError с ошибкой о max_length
        """
        with pytest.raises(ValidationError) as exc_info:
            STaskPatch(title="A" * 201)
        errors = exc_info.value.errors()
        assert any("max_length" in str(err) for err in errors)


# ============================================================
# STask — схема для ответа API (GET, PUT, PATCH)
# ============================================================

class TestSTask:
    """Тесты для схемы ответа API."""

    def _make_task_model(self, task_id=1):
        """Вспомогательный метод: создаёт TaskModel с заполненными полями."""
        from models.tasks import TaskModel
        task_model = TaskModel()
        task_model.id = task_id
        task_model.title = "Test"
        task_model.description = "Desc"
        task_model.is_completed = True
        task_model.priority = 3
        task_model.user_id = None
        return task_model

    def test_from_attributes(self):
        """
        Arrange: ORM-модель TaskModel
        Act: STask.model_validate(task_model)
        Assert: все поля совпадают
        """
        task_model = self._make_task_model()

        task = STask.model_validate(task_model)
        assert task.id == 1
        assert task.title == "Test"
        assert task.description == "Desc"
        assert task.is_completed is True
        assert task.priority == 3
        assert task.user_id is None

    def test_from_attributes_null_description(self):
        """
        Arrange: ORM-модель с description=None и user_id
        Act: STask.model_validate(task_model)
        Assert: description is None, user_id пробрасывается
        """
        task_model = self._make_task_model(task_id=2)
        task_model.description = None
        task_model.user_id = 7

        task = STask.model_validate(task_model)
        assert task.id == 2
        assert task.description is None
        assert task.user_id == 7
        assert task.is_completed is True