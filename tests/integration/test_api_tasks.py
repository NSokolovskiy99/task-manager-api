"""
Интеграционные тесты для CRUD endpoints задач.

Использует in-memory SQLite через фикстуру client.
Каждый тест работает с чистой БД (фикстура test_session создаётся заново).
"""

import pytest


class TestCreateTask:
    """Тесты для POST /tasks/."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_task_success(self, client):
        """
        Arrange: данные для создания задачи
        Act: POST /tasks/
        Assert: status_code == 201, все поля корректны
        """
        response = await client.post(
            "/tasks/",
            json={"name": "Test Task", "description": "Test Description"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Task"
        assert data["description"] == "Test Description"
        assert data["is_completed"] is False
        assert isinstance(data["id"], int)
        assert data["id"] > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_task_minimal(self, client):
        """
        Arrange: только name (минимальные данные)
        Act: POST /tasks/
        Assert: status_code == 201, description is None, is_completed is False
        """
        response = await client.post(
            "/tasks/",
            json={"name": "Minimal"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal"
        assert data["description"] is None
        assert data["is_completed"] is False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_task_validation_error_name_short(self, client):
        """
        Arrange: name короче 3 символов
        Act: POST /tasks/
        Assert: status_code == 422
        """
        response = await client.post(
            "/tasks/",
            json={"name": "AB"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_task_validation_error_name_long(self, client):
        """
        Arrange: name длиннее 100 символов
        Act: POST /tasks/
        Assert: status_code == 422
        """
        response = await client.post(
            "/tasks/",
            json={"name": "A" * 101},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_task_validation_error_description_long(self, client):
        """
        Arrange: description длиннее 500 символов
        Act: POST /tasks/
        Assert: status_code == 422
        """
        response = await client.post(
            "/tasks/",
            json={"name": "Valid Name", "description": "A" * 501},
        )

        assert response.status_code == 422


class TestGetTasks:
    """Тесты для GET /tasks/."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_tasks_empty(self, client):
        """
        Arrange: БД пуста
        Act: GET /tasks/
        Assert: status_code == 200, пустой список
        """
        response = await client.get("/tasks/")

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_tasks_with_pagination(self, client):
        """
        Arrange: создаём 25 задач
        Act: GET /tasks/?skip=0&limit=10
        Assert: вернулось 10 задач
        """
        # Создаём 25 задач
        for i in range(25):
            await client.post(
                "/tasks/",
                json={"name": f"Task {i}"},
            )

        response = await client.get("/tasks/?skip=0&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_tasks_second_page(self, client):
        """
        Arrange: создаём 25 задач
        Act: GET /tasks/?skip=10&limit=10
        Assert: вернулось 10 задач, ID не пересекаются с первой страницей
        """
        # Создаём 25 задач
        for i in range(25):
            await client.post(
                "/tasks/",
                json={"name": f"Task {i}"},
            )

        # Первая страница
        page1 = await client.get("/tasks/?skip=0&limit=10")
        page1_ids = {task["id"] for task in page1.json()}

        # Вторая страница
        page2 = await client.get("/tasks/?skip=10&limit=10")
        page2_data = page2.json()
        page2_ids = {task["id"] for task in page2_data}

        assert len(page2_data) == 10
        assert page1_ids.isdisjoint(page2_ids), "ID страниц пересекаются"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_tasks_filter_completed(self, client):
        """
        Arrange: создаём completed и not completed задачи
        Act: GET /tasks/?is_completed=true
        Assert: все задачи в ответе имеют is_completed=True
        """
        # Создаём completed задачу
        await client.post(
            "/tasks/",
            json={"name": "Completed Task", "is_completed": True},
        )
        # Создаём not completed задачу
        await client.post(
            "/tasks/",
            json={"name": "Not Completed Task"},
        )

        response = await client.get("/tasks/?is_completed=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_completed"] is True
        assert data[0]["name"] == "Completed Task"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_tasks_filter_not_completed(self, client):
        """
        Arrange: создаём completed и not completed задачи
        Act: GET /tasks/?is_completed=false
        Assert: все задачи в ответе имеют is_completed=False
        """
        # Создаём completed задачу
        await client.post(
            "/tasks/",
            json={"name": "Completed Task", "is_completed": True},
        )
        # Создаём not completed задачу
        await client.post(
            "/tasks/",
            json={"name": "Not Completed Task"},
        )

        response = await client.get("/tasks/?is_completed=false")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_completed"] is False
        assert data[0]["name"] == "Not Completed Task"


class TestGetTaskById:
    """Тесты для GET /tasks/{id}."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_task_by_id_success(self, client, created_task):
        """
        Arrange: создана задача через created_task
        Act: GET /tasks/{id}
        Assert: status_code == 200, поля совпадают
        """
        task_id = created_task["id"]
        response = await client.get(f"/tasks/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["name"] == "Test Task"
        assert data["description"] == "Test Description"
        assert data["is_completed"] is False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_task_by_id_not_found(self, client):
        """
        Arrange: —
        Act: GET /tasks/9999
        Assert: status_code == 404
        """
        response = await client.get("/tasks/9999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestUpdateFullTask:
    """Тесты для PUT /tasks/{id}."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_full_task_success(self, client, created_task):
        """
        Arrange: создана задача, подготовлены новые данные
        Act: PUT /tasks/{id}
        Assert: status_code == 200, все поля обновлены
        """
        task_id = created_task["id"]
        response = await client.put(
            f"/tasks/{task_id}",
            json={
                "name": "Updated Task",
                "description": "Updated Description",
                "is_completed": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Task"
        assert data["description"] == "Updated Description"
        assert data["is_completed"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_full_task_not_found(self, client):
        """
        Arrange: —
        Act: PUT /tasks/9999
        Assert: status_code == 404
        """
        response = await client.put(
            "/tasks/9999",
            json={
                "name": "Updated",
                "description": "Desc",
                "is_completed": False,
            },
        )

        assert response.status_code == 404


class TestPatchTask:
    """Тесты для PATCH /tasks/{id}."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_patch_task_is_completed_only(self, client, created_task):
        """
        Arrange: создана задача, меняем только is_completed
        Act: PATCH /tasks/{id}
        Assert: status_code == 200, is_completed=True, name не изменился
        """
        task_id = created_task["id"]
        response = await client.patch(
            f"/tasks/{task_id}",
            json={"is_completed": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_completed"] is True
        assert data["name"] == "Test Task"  # не изменилось
        assert data["description"] == "Test Description"  # не изменилось

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_patch_task_name_only(self, client, created_task):
        """
        Arrange: создана задача, меняем только name
        Act: PATCH /tasks/{id}
        Assert: status_code == 200, name обновлён, is_completed не изменился
        """
        task_id = created_task["id"]
        response = await client.patch(
            f"/tasks/{task_id}",
            json={"name": "New Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["is_completed"] is False  # не изменилось

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_patch_task_no_changes(self, client, created_task):
        """
        Arrange: создана задача, отправляем пустой PATCH
        Act: PATCH /tasks/{id} с {}
        Assert: status_code == 200, задача не изменилась
        """
        task_id = created_task["id"]
        response = await client.patch(
            f"/tasks/{task_id}",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Task"
        assert data["description"] == "Test Description"
        assert data["is_completed"] is False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_patch_task_not_found(self, client):
        """
        Arrange: —
        Act: PATCH /tasks/9999
        Assert: status_code == 404
        """
        response = await client.patch(
            "/tasks/9999",
            json={"name": "Updated"},
        )

        assert response.status_code == 404


class TestDeleteTask:
    """Тесты для DELETE /tasks/{id}."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_task_success(self, client, created_task):
        """
        Arrange: создана задача
        Act: DELETE /tasks/{id}
        Assert: status_code == 204, GET /tasks/{id} → 404
        """
        task_id = created_task["id"]
        response = await client.delete(f"/tasks/{task_id}")

        assert response.status_code == 204

        # Проверяем, что задача действительно удалена
        get_response = await client.get(f"/tasks/{task_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_task_not_found(self, client):
        """
        Arrange: —
        Act: DELETE /tasks/9999
        Assert: status_code == 404
        """
        response = await client.delete("/tasks/9999")

        assert response.status_code == 404