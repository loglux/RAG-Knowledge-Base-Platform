"""Integration tests for Knowledge Bases API."""

import pytest
from httpx import AsyncClient

from app.models.database import KnowledgeBase


@pytest.mark.integration
@pytest.mark.asyncio
class TestKnowledgeBasesAPI:
    """Test Knowledge Bases CRUD endpoints."""

    async def test_create_knowledge_base(self, test_client: AsyncClient, mock_kb_data: dict):
        """Test creating a new knowledge base."""
        response = await test_client.post("/api/v1/knowledge-bases/", json=mock_kb_data)

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == mock_kb_data["name"]
        assert data["description"] == mock_kb_data["description"]
        assert "id" in data
        assert "collection_name" in data

    async def test_list_knowledge_bases(self, test_client: AsyncClient, sample_kb: KnowledgeBase):
        """Test listing knowledge bases."""
        response = await test_client.get("/api/v1/knowledge-bases/")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    async def test_get_knowledge_base(self, test_client: AsyncClient, sample_kb: KnowledgeBase):
        """Test getting a specific knowledge base."""
        response = await test_client.get(f"/api/v1/knowledge-bases/{sample_kb.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(sample_kb.id)
        assert data["name"] == sample_kb.name

    async def test_get_nonexistent_knowledge_base(self, test_client: AsyncClient):
        """Test getting a non-existent knowledge base returns 404."""
        from uuid import uuid4

        fake_id = uuid4()

        response = await test_client.get(f"/api/v1/knowledge-bases/{fake_id}")

        assert response.status_code == 404

    async def test_update_knowledge_base(self, test_client: AsyncClient, sample_kb: KnowledgeBase):
        """Test updating a knowledge base."""
        update_data = {"name": "Updated Name", "description": "Updated description"}

        response = await test_client.put(
            f"/api/v1/knowledge-bases/{sample_kb.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]

    async def test_delete_knowledge_base(self, test_client: AsyncClient, sample_kb: KnowledgeBase):
        """Test deleting a knowledge base."""
        response = await test_client.delete(f"/api/v1/knowledge-bases/{sample_kb.id}")

        assert response.status_code == 204

        # Verify it's deleted (soft delete)
        get_response = await test_client.get(f"/api/v1/knowledge-bases/{sample_kb.id}")
        assert get_response.status_code == 404
