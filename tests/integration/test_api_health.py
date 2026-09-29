"""
Интеграционные тесты для healthcheck endpoint.

Проверяет, что сервер отвечает на GET /health.
"""

import pytest


class TestHealth:
    """Тесты для /health endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_endpoint(self, client):
        """
        Arrange: —
        Act: GET /health
        Assert: status_code == 200, ответ содержит ожидаемые поля
        """
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "task-api"}