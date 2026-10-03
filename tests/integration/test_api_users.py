"""
Интеграционные тесты для CRUD endpoints пользователей.

Использует in-memory SQLite через фикстуру client.
Каждый тест работает с чистой БД (фикстура test_session создаётся заново).
"""

import pytest


class TestCreateUser:
    """Тесты для POST /users/."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_user_success(self, client):
        """
        Arrange: данные для создания пользователя
        Act: POST /users/
        Assert: status_code == 201, все поля корректны
        """
        response = await client.post(
            "/users/",
            json={"name": "Ivan", "email": "ivan@example.com"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Ivan"
        assert data["email"] == "ivan@example.com"
        assert data["is_active"] is True  # значение по умолчанию
        assert isinstance(data["id"], int)
        assert data["id"] > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_user_with_is_active_false(self, client):
        """
        Arrange: явно передаём is_active=False
        Act: POST /users/
        Assert: status_code == 201, is_active=False
        """
        response = await client.post(
            "/users/",
            json={"name": "Petr", "email": "petr@example.com", "is_active": False},
        )

        assert response.status_code == 201
        assert response.json()["is_active"] is False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_user_duplicate_email(self, client, created_user):
        """
        Arrange: пользователь с email уже существует
        Act: POST /users/ с тем же email
        Assert: status_code == 400
        """
        response = await client.post(
            "/users/",
            json={"name": "Another", "email": created_user["email"]},
        )

        assert response.status_code == 400
        assert created_user["email"] in response.json()["detail"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_user_invalid_email(self, client):
        """
        Arrange: некорректный email
        Act: POST /users/
        Assert: status_code == 422
        """
        response = await client.post(
            "/users/",
            json={"name": "Ivan", "email": "not-an-email"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_user_empty_name(self, client):
        """
        Arrange: пустой name
        Act: POST /users/
        Assert: status_code == 422
        """
        response = await client.post(
            "/users/",
            json={"name": "", "email": "ivan@example.com"},
        )

        assert response.status_code == 422


class TestGetUsers:
    """Тесты для GET /users/."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_users_empty(self, client):
        """
        Arrange: БД пуста
        Act: GET /users/
        Assert: status_code == 200, пустой список
        """
        response = await client.get("/users/")

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_users_with_pagination(self, client):
        """
        Arrange: создаём 25 пользователей
        Act: GET /users/?skip=0&limit=10
        Assert: вернулось 10 пользователей
        """
        for i in range(25):
            await client.post(
                "/users/",
                json={"name": f"User {i}", "email": f"user{i}@example.com"},
            )

        response = await client.get("/users/?skip=0&limit=10")

        assert response.status_code == 200
        assert len(response.json()) == 10

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_users_filter_has_completed_tasks(self, client, created_user):
        """
        Arrange: у пользователя есть выполненная задача
        Act: GET /users/?has_completed_tasks=true
        Assert: вернулся пользователь
        """
        await client.post(
            "/tasks/",
            json={
                "title": "Done Task",
                "priority": 3,
                "user_id": created_user["id"],
                "is_completed": True,
            },
        )

        response = await client.get("/users/?has_completed_tasks=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == created_user["id"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_users_filter_has_uncompleted_tasks(self, client, created_user):
        """
        Arrange: у пользователя есть невыполненная задача
        Act: GET /users/?has_completed_tasks=false
        Assert: вернулся пользователь
        """
        await client.post(
            "/tasks/",
            json={
                "title": "Pending Task",
                "priority": 3,
                "user_id": created_user["id"],
                "is_completed": False,
            },
        )

        response = await client.get("/users/?has_completed_tasks=false")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == created_user["id"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_users_filter_excludes_users_without_matching_tasks(
        self, client, created_user
    ):
        """
        Arrange: у пользователя только невыполненная задача
        Act: GET /users/?has_completed_tasks=true
        Assert: пользователь НЕ попадает в выборку (нет выполненных задач)
        """
        await client.post(
            "/tasks/",
            json={
                "title": "Pending Task",
                "priority": 3,
                "user_id": created_user["id"],
                "is_completed": False,
            },
        )

        response = await client.get("/users/?has_completed_tasks=true")

        assert response.status_code == 200
        assert response.json() == []


class TestGetUserById:
    """Тесты для GET /users/{id}."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_user_by_id_success(self, client, created_user):
        """
        Arrange: создан пользователь
        Act: GET /users/{id}
        Assert: status_code == 200, поля совпадают
        """
        user_id = created_user["id"]
        response = await client.get(f"/users/{user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["name"] == "Test User"
        assert data["email"] == "test@example.com"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_user_by_id_not_found(self, client):
        """
        Arrange: —
        Act: GET /users/9999
        Assert: status_code == 404
        """
        response = await client.get("/users/9999")

        assert response.status_code == 404
        assert "9999" in response.json()["detail"]


class TestGetUserWithTasks:
    """Тесты для GET /users/{id}/tasks."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_user_with_tasks_empty(self, client, created_user):
        """
        Arrange: у пользователя нет задач
        Act: GET /users/{id}/tasks
        Assert: status_code == 200, tasks == []
        """
        user_id = created_user["id"]
        response = await client.get(f"/users/{user_id}/tasks")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["name"] == "Test User"
        assert data["tasks"] == []

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_user_with_tasks_success(self, client, created_user):
        """
        Arrange: у пользователя есть одна задача
        Act: GET /users/{id}/tasks
        Assert: status_code == 200, в tasks одна задача с корректными полями
        """
        await client.post(
            "/tasks/",
            json={"title": "My Task", "priority": 3, "user_id": created_user["id"]},
        )

        user_id = created_user["id"]
        response = await client.get(f"/users/{user_id}/tasks")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert len(data["tasks"]) == 1
        task = data["tasks"][0]
        assert task["title"] == "My Task"
        assert task["priority"] == 3
        assert task["user_id"] == user_id

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_user_with_tasks_not_found(self, client):
        """
        Arrange: —
        Act: GET /users/9999/tasks
        Assert: status_code == 404
        """
        response = await client.get("/users/9999/tasks")

        assert response.status_code == 404


class TestUpdateFullUser:
    """Тесты для PUT /users/{id}."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_full_user_success(self, client, created_user):
        """
        Arrange: создан пользователь
        Act: PUT /users/{id}
        Assert: status_code == 200, все поля обновлены
        """
        user_id = created_user["id"]
        response = await client.put(
            f"/users/{user_id}",
            json={
                "name": "Updated User",
                "email": "updated@example.com",
                "is_active": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated User"
        assert data["email"] == "updated@example.com"
        assert data["is_active"] is False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_full_user_not_found(self, client):
        """
        Arrange: —
        Act: PUT /users/9999
        Assert: status_code == 404
        """
        response = await client.put(
            "/users/9999",
            json={"name": "Updated", "email": "updated@example.com"},
        )

        assert response.status_code == 404


class TestPatchUser:
    """Тесты для PATCH /users/{id}."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_patch_user_name_only(self, client, created_user):
        """
        Arrange: создан пользователь
        Act: PATCH /users/{id} с name
        Assert: status_code == 200, name обновлён, email не изменился
        """
        user_id = created_user["id"]
        response = await client.patch(
            f"/users/{user_id}",
            json={"name": "New Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["email"] == "test@example.com"  # не изменилось
        assert data["is_active"] is True  # не изменилось

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_patch_user_is_active_only(self, client, created_user):
        """
        Arrange: создан пользователь
        Act: PATCH /users/{id} с is_active=False
        Assert: status_code == 200, is_active=False, name не изменился
        """
        user_id = created_user["id"]
        response = await client.patch(
            f"/users/{user_id}",
            json={"is_active": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        assert data["name"] == "Test User"  # не изменилось

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_patch_user_no_changes(self, client, created_user):
        """
        Arrange: создан пользователь
        Act: PATCH /users/{id} с {}
        Assert: status_code == 200, пользователь не изменился
        """
        user_id = created_user["id"]
        response = await client.patch(
            f"/users/{user_id}",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test User"
        assert data["email"] == "test@example.com"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_patch_user_extra_field_forbidden(self, client, created_user):
        """
        Arrange: создан пользователь
        Act: PATCH /users/{id} с лишним полем
        Assert: status_code == 422 (extra="forbid")
        """
        user_id = created_user["id"]
        response = await client.patch(
            f"/users/{user_id}",
            json={"unknown_field": "value"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_patch_user_not_found(self, client):
        """
        Arrange: —
        Act: PATCH /users/9999
        Assert: status_code == 404
        """
        response = await client.patch(
            "/users/9999",
            json={"name": "Updated"},
        )

        assert response.status_code == 404


class TestDeleteUser:
    """Тесты для DELETE /users/{id}."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_user_success(self, client, created_user):
        """
        Arrange: создан пользователь
        Act: DELETE /users/{id}
        Assert: status_code == 204, GET /users/{id} → 404
        """
        user_id = created_user["id"]
        response = await client.delete(f"/users/{user_id}")

        assert response.status_code == 204

        # Проверяем, что пользователь действительно удалён
        get_response = await client.get(f"/users/{user_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_user_not_found(self, client):
        """
        Arrange: —
        Act: DELETE /users/9999
        Assert: status_code == 404
        """
        response = await client.delete("/users/9999")

        assert response.status_code == 404