"""
Интеграционные тесты для обработки ошибок API.

Проверяет корректность HTTP-статусов при невалидных запросах.
"""

import pytest


class TestApiErrors:
    """Тесты для обработки ошибок API."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_method(self, client):
        """
        Arrange: —
        Act: PUT /tasks/ (POST-only endpoint)
        Assert: status_code == 405
        """
        response = await client.put(
            "/tasks/",
            json={"name": "Test"},
        )

        assert response.status_code == 405

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_content_type(self, client):
        """
        Arrange: отправляем не JSON
        Act: POST /tasks/ с content-type text/plain
        Assert: status_code == 422
        """
        response = await client.post(
            "/tasks/",
            content="not json",
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 422