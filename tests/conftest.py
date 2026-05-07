"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.dependencies import get_current_user, get_current_user_id
from app.main import app
from app.models.database import Document, KnowledgeBase
from app.models.enums import ChunkingStrategy, DocumentStatus, FileType

# ============================================================================
# Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================

# Test database URL (using a separate test database)
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/knowledge_base", "/knowledge_base_test")


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


# ============================================================================
# FastAPI Test Client
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def test_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override."""

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return 1

    async def override_get_current_user_id():
        return uuid4()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch):
    """Prevent integration tests from calling external vector/lexical services."""

    class _FakeVectorStore:
        async def create_collection(self, *args, **kwargs):
            return True

        async def collection_exists(self, *args, **kwargs):
            return True

        async def delete_collection(self, *args, **kwargs):
            return True

    class _FakeLexicalStore:
        async def delete_by_kb_id(self, *args, **kwargs):
            return None

    class _FakeDocumentProcessor:
        async def process_document(self, *args, **kwargs):
            return True

    monkeypatch.setattr("app.api.v1.knowledge_bases.get_vector_store", lambda: _FakeVectorStore())
    monkeypatch.setattr("app.core.vector_store.get_vector_store", lambda: _FakeVectorStore())
    monkeypatch.setattr("app.api.v1.knowledge_bases.get_lexical_store", lambda: _FakeLexicalStore())
    monkeypatch.setattr("app.core.lexical_store.get_lexical_store", lambda: _FakeLexicalStore())
    monkeypatch.setattr(
        "app.api.v1.documents.get_document_processor",
        lambda: _FakeDocumentProcessor(),
    )


# ============================================================================
# Mock Data Fixtures
# ============================================================================


@pytest.fixture
def mock_kb_data() -> dict:
    """Mock knowledge base data."""
    return {
        "name": "Test Knowledge Base",
        "description": "A test knowledge base for unit tests",
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "chunking_strategy": ChunkingStrategy.FIXED_SIZE,
    }


@pytest.fixture
def mock_document_data() -> dict:
    """Mock document data."""
    return {
        "filename": "test.md",
        "content": "# Test Document\n\nThis is a test document for unit tests.\n\nIt has multiple lines.",
        "file_type": FileType.MD,
    }


@pytest_asyncio.fixture
async def sample_kb(test_db: AsyncSession, mock_kb_data: dict) -> KnowledgeBase:
    """Create a sample knowledge base in test database."""
    kb = KnowledgeBase(
        **mock_kb_data,
        collection_name=f"test_kb_{uuid4().hex[:16]}",
    )

    test_db.add(kb)
    await test_db.commit()
    await test_db.refresh(kb)

    return kb


@pytest_asyncio.fixture
async def sample_document(
    test_db: AsyncSession, sample_kb: KnowledgeBase, mock_document_data: dict
) -> Document:
    """Create a sample document in test database."""
    import hashlib

    content = mock_document_data["content"]
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    doc = Document(
        knowledge_base_id=sample_kb.id,
        filename=mock_document_data["filename"],
        file_type=mock_document_data["file_type"],
        content=content,
        content_hash=content_hash,
        file_size=len(content.encode()),
        status=DocumentStatus.PENDING,
    )

    test_db.add(doc)
    await test_db.commit()
    await test_db.refresh(doc)

    return doc


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def sample_text() -> str:
    """Sample text for chunking and processing tests."""
    return """
    This is a sample text for testing text processing functionality.
    It contains multiple sentences and paragraphs.

    The second paragraph has more content to test chunking strategies.
    We want to ensure that the text is properly split into chunks.

    Finally, the third paragraph concludes our sample text.
    This should be enough content for basic testing purposes.
    """


@pytest.fixture
def sample_markdown() -> str:
    """Sample markdown content for testing."""
    return """
# Main Title

This is a markdown document with various elements.

## Section 1

Some content in section 1.

- List item 1
- List item 2
- List item 3

## Section 2

More content in section 2 with **bold** and *italic* text.

```python
# Code block
def hello():
    print("Hello, World!")
```

## Conclusion

Final thoughts and summary.
"""


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings after each test."""
    yield
    # Settings are cached, so we need to clear cache
    from app.config import get_settings

    get_settings.cache_clear()


# ============================================================================
# Markers
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
