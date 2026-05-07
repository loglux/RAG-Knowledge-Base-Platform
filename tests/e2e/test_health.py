"""End-to-end tests for health endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
@pytest.mark.asyncio
class TestHealthEndpoints:
    """Test health check endpoints."""

    async def test_health_check(self, test_client: AsyncClient):
        """Test basic health check endpoint."""
        response = await test_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert "timestamp" in data

    async def test_readiness_check(self, test_client: AsyncClient):
        """Test readiness check endpoint."""
        response = await test_client.get("/api/v1/ready")

        assert response.status_code in [200, 503]
        data = response.json()

        assert "ready" in data
        assert "checks" in data
        assert "database" in data["checks"]

    async def test_info_endpoint(self, test_client: AsyncClient):
        """Test API info endpoint."""
        response = await test_client.get("/api/v1/info")

        assert response.status_code == 200
        data = response.json()

        assert "version" in data
        assert "environment" in data
        assert "features" in data
        assert "supported_formats" in data

    async def test_root_endpoint(self, test_client: AsyncClient):
        """Test root endpoint."""
        response = await test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Knowledge Base Platform API"
        assert "version" in data
        assert "docs" in data
