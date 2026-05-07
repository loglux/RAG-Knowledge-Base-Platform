"""Integration tests for Documents API."""

import pytest
from httpx import AsyncClient

from app.models.database import Document, KnowledgeBase


@pytest.mark.integration
@pytest.mark.asyncio
class TestDocumentsAPI:
    """Test Documents CRUD endpoints."""

    async def test_create_document(
        self, test_client: AsyncClient, sample_kb: KnowledgeBase, mock_document_data: dict
    ):
        """Test creating a new document."""
        request_data = {**mock_document_data, "knowledge_base_id": str(sample_kb.id)}

        response = await test_client.post("/api/v1/documents/", json=request_data)

        assert response.status_code == 201
        data = response.json()

        assert data["filename"] == mock_document_data["filename"]
        assert data["knowledge_base_id"] == str(sample_kb.id)
        assert data["status"] == "pending"
        assert "id" in data

    async def test_create_duplicate_document(
        self, test_client: AsyncClient, sample_document: Document, mock_document_data: dict
    ):
        """Test creating duplicate document returns 409."""
        request_data = {
            **mock_document_data,
            "knowledge_base_id": str(sample_document.knowledge_base_id),
        }

        response = await test_client.post("/api/v1/documents/", json=request_data)

        assert response.status_code == 409

    async def test_list_documents(self, test_client: AsyncClient, sample_document: Document):
        """Test listing documents."""
        response = await test_client.get("/api/v1/documents/")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_list_documents_by_knowledge_base(
        self, test_client: AsyncClient, sample_document: Document
    ):
        """Test filtering documents by knowledge base."""
        response = await test_client.get(
            f"/api/v1/documents/?knowledge_base_id={sample_document.knowledge_base_id}"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] >= 1
        for doc in data["items"]:
            assert doc["knowledge_base_id"] == str(sample_document.knowledge_base_id)

    async def test_get_document(self, test_client: AsyncClient, sample_document: Document):
        """Test getting a specific document."""
        response = await test_client.get(f"/api/v1/documents/{sample_document.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(sample_document.id)
        assert data["filename"] == sample_document.filename
        assert "content" in data

    async def test_delete_document(self, test_client: AsyncClient, sample_document: Document):
        """Test deleting a document."""
        response = await test_client.delete(f"/api/v1/documents/{sample_document.id}")

        assert response.status_code == 204

        # Verify it's deleted
        get_response = await test_client.get(f"/api/v1/documents/{sample_document.id}")
        assert get_response.status_code == 404
