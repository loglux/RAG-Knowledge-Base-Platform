"""Integration tests for the FastMCP tool registry in app.mcp.server.

These tools call get_db_session() directly instead of going through FastAPI's
Depends(get_db), so the test_client dependency-override pattern used elsewhere
doesn't apply here — instead we point app.db.session's global session factory
at the test engine (see the mcp_db fixture below).
"""

import asyncio
import json
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.db.session as db_session_module
from app.config import Settings, settings
from app.mcp.server import MCP_TOOL_NAMES, build_mcp_app
from app.models.database import Document, KnowledgeBase


def _text(result) -> str:
    """Extract the text payload from a FastMCP ToolResult."""
    return str(result.content[0].text)


async def _call(mcp_app, tool_name: str, **kwargs) -> str:
    result = await mcp_app.call_tool(tool_name, kwargs)
    return _text(result)


@pytest_asyncio.fixture
async def mcp_db(test_engine, monkeypatch):
    """Point app.db.session's global session factory at the test engine.

    MCP tools call get_db_session()/AsyncSessionLocal directly rather than the
    FastAPI get_db dependency that test_client overrides, so we have to patch
    the module globals instead.
    """
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(db_session_module, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(db_session_module, "engine", test_engine)
    yield session_factory


@pytest_asyncio.fixture
async def mcp_app(mcp_db, monkeypatch):
    """Build a fresh MCP app with every tool enabled and external services stubbed."""
    monkeypatch.setattr(settings, "MCP_TOOLS_ENABLED", list(MCP_TOOL_NAMES))

    created_tasks: list = []

    def fake_create_task(coro):
        task = asyncio.ensure_future(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr("app.mcp.server.asyncio.create_task", fake_create_task)

    class _FakeVectorStore:
        async def create_collection(self, *args, **kwargs):
            return True

    monkeypatch.setattr("app.mcp.server.get_vector_store", lambda: _FakeVectorStore())

    class _FakeDocumentProcessor:
        async def process_document(self, *args, **kwargs):
            return True

    monkeypatch.setattr("app.mcp.server.get_document_processor", lambda: _FakeDocumentProcessor())

    app_ = build_mcp_app()
    app_._test_background_tasks = created_tasks  # type: ignore[attr-defined]
    yield app_


async def _drain_background_tasks(mcp_app) -> None:
    """Await any asyncio.create_task()'d background work spawned by a tool call."""
    tasks = mcp_app._test_background_tasks
    if tasks:
        await asyncio.gather(*tasks)
        tasks.clear()


# ============================================================================
# Registry consistency (regression guard)
# ============================================================================


def test_default_enabled_tools_cover_full_registry():
    """config.py's env-var fallback must list every tool server.py registers.

    Regression test: MCP_TOOLS_ENABLED's default previously only listed the
    original 8 tools, so create_knowledge_base/ingest_url/ingest_text silently
    reported as disabled on any install that never explicitly saved MCP
    settings through the admin UI (no DB override row yet).
    """
    default_enabled = set(Settings.model_fields["MCP_TOOLS_ENABLED"].default)
    assert default_enabled == set(MCP_TOOL_NAMES)


# ============================================================================
# Read-only tools
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestListKnowledgeBases:
    async def test_empty(self, mcp_app):
        text = await _call(mcp_app, "list_knowledge_bases")
        assert text == "No knowledge bases found."

    async def test_with_kb(self, mcp_app, sample_kb: KnowledgeBase):
        text = await _call(mcp_app, "list_knowledge_bases")
        assert sample_kb.name in text
        assert str(sample_kb.id) in text


@pytest.mark.integration
@pytest.mark.asyncio
class TestListDocuments:
    async def test_missing_kb(self, mcp_app):
        text = await _call(mcp_app, "list_documents", knowledge_base_id=str(uuid4()))
        assert text == "Error: knowledge_base_id is required."

    async def test_empty(self, mcp_app, sample_kb: KnowledgeBase):
        text = await _call(mcp_app, "list_documents", knowledge_base_id=str(sample_kb.id))
        assert text == "No documents found for this knowledge base."

    async def test_with_document(
        self, mcp_app, sample_kb: KnowledgeBase, sample_document: Document
    ):
        text = await _call(mcp_app, "list_documents", knowledge_base_id=str(sample_kb.id))
        assert sample_document.filename in text
        assert str(sample_document.id) in text


# ============================================================================
# Retrieval settings tools
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestRetrievalSettings:
    async def test_get_settings_missing_kb(self, mcp_app):
        text = await _call(mcp_app, "get_kb_retrieval_settings", knowledge_base_id=str(uuid4()))
        assert text == "Error: knowledge_base_id is required."

    async def test_get_default_settings(self, mcp_app, sample_kb: KnowledgeBase):
        text = await _call(
            mcp_app, "get_kb_retrieval_settings", knowledge_base_id=str(sample_kb.id)
        )
        payload = json.loads(text)
        assert payload["stored"] == {}

    async def test_set_then_get_settings(self, mcp_app, sample_kb: KnowledgeBase):
        set_result = await _call(
            mcp_app,
            "set_kb_retrieval_settings",
            knowledge_base_id=str(sample_kb.id),
            settings_payload={"top_k": 7},
        )
        assert set_result == "OK"

        text = await _call(
            mcp_app, "get_kb_retrieval_settings", knowledge_base_id=str(sample_kb.id)
        )
        payload = json.loads(text)
        assert payload["stored"]["top_k"] == 7
        assert payload["effective"]["top_k"] == 7

    async def test_clear_settings(self, mcp_app, sample_kb: KnowledgeBase):
        await _call(
            mcp_app,
            "set_kb_retrieval_settings",
            knowledge_base_id=str(sample_kb.id),
            settings_payload={"top_k": 7},
        )
        clear_result = await _call(
            mcp_app, "clear_kb_retrieval_settings", knowledge_base_id=str(sample_kb.id)
        )
        assert clear_result == "OK"

        text = await _call(
            mcp_app, "get_kb_retrieval_settings", knowledge_base_id=str(sample_kb.id)
        )
        payload = json.loads(text)
        assert payload["stored"] == {}

    async def test_get_effective_settings(self, mcp_app, sample_kb: KnowledgeBase):
        text = await _call(
            mcp_app, "get_kb_effective_settings", knowledge_base_id=str(sample_kb.id)
        )
        payload = json.loads(text)
        assert payload["knowledge_base"]["id"] == str(sample_kb.id)
        assert payload["knowledge_base"]["name"] == sample_kb.name
        assert "retrieval" in payload


# ============================================================================
# create_knowledge_base
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestCreateKnowledgeBase:
    async def test_creates_kb_with_valid_collection_name(self, mcp_app, mcp_db):
        """Regression test for the kb_id_to_collection_name import bug: this
        tool previously raised ImportError on every call because it imported
        the helper from app.core.vector_store instead of
        app.api.v1.knowledge_bases, where it actually lives."""
        text = await _call(mcp_app, "create_knowledge_base", name="My New KB")
        assert text.startswith("Created knowledge base 'My New KB'")

        async with mcp_db() as db:
            result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.name == "My New KB")
            )
            kb = result.scalar_one()
            assert kb.collection_name
            assert kb.embedding_model == "text-embedding-3-large"

    async def test_unknown_embedding_model(self, mcp_app):
        text = await _call(mcp_app, "create_knowledge_base", name="Bad KB", embedding_model="nope")
        assert text.startswith("Error: unknown embedding_model")


# ============================================================================
# ingest_text / ingest_url
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestIngestText:
    async def test_missing_kb(self, mcp_app):
        text = await _call(
            mcp_app,
            "ingest_text",
            knowledge_base_id=str(uuid4()),
            content="hello world",
        )
        assert text == "Error: knowledge_base_id not found."

    async def test_empty_content(self, mcp_app, sample_kb: KnowledgeBase):
        text = await _call(
            mcp_app, "ingest_text", knowledge_base_id=str(sample_kb.id), content="   "
        )
        assert text == "Error: content cannot be empty."

    async def test_ingest_creates_document(self, mcp_app, sample_kb: KnowledgeBase, mcp_db):
        text = await _call(
            mcp_app,
            "ingest_text",
            knowledge_base_id=str(sample_kb.id),
            content="# Hello\n\nSome content.",
            title="My Doc",
        )
        assert text.startswith("Ingested 'My Doc.md'")
        await _drain_background_tasks(mcp_app)

        async with mcp_db() as db:
            result = await db.execute(
                select(Document).where(Document.knowledge_base_id == sample_kb.id)
            )
            doc = result.scalar_one()
            assert doc.filename == "My Doc.md"
            assert doc.content == "# Hello\n\nSome content."

    async def test_duplicate_content_rejected(self, mcp_app, sample_kb: KnowledgeBase):
        content = "Duplicate content check."
        first = await _call(
            mcp_app, "ingest_text", knowledge_base_id=str(sample_kb.id), content=content
        )
        assert first.startswith("Ingested")
        await _drain_background_tasks(mcp_app)

        second = await _call(
            mcp_app, "ingest_text", knowledge_base_id=str(sample_kb.id), content=content
        )
        assert second.startswith("Error: identical content already indexed")


@pytest.mark.integration
@pytest.mark.asyncio
class TestIngestUrl:
    async def test_missing_kb(self, mcp_app):
        text = await _call(
            mcp_app,
            "ingest_url",
            knowledge_base_id=str(uuid4()),
            url="https://example.com/article",
        )
        assert text == "Error: knowledge_base_id not found."

    async def test_ingest_url_creates_document(
        self, mcp_app, sample_kb: KnowledgeBase, mcp_db, monkeypatch
    ):
        class _FakePage:
            content_md = "# Article\n\nBody text."
            canonical_url = None
            title = "Article Title"
            author = None
            publish_date = None
            sitename = None
            description = None
            language = "en"

        async def fake_extract_url(url: str):
            return _FakePage()

        monkeypatch.setattr("app.services.url_extractor_client.extract_url", fake_extract_url)

        text = await _call(
            mcp_app,
            "ingest_url",
            knowledge_base_id=str(sample_kb.id),
            url="https://example.com/article?utm_source=test",
        )
        assert text.startswith("Ingested 'Article Title.md'")
        assert "utm_source" not in text
        await _drain_background_tasks(mcp_app)

        async with mcp_db() as db:
            result = await db.execute(
                select(Document).where(Document.knowledge_base_id == sample_kb.id)
            )
            doc = result.scalar_one()
            assert doc.source_url == "https://example.com/article"

    async def test_url_extraction_failure(self, mcp_app, sample_kb: KnowledgeBase, monkeypatch):
        from app.services.url_extractor_client import Url2mdExtractionError

        async def fake_extract_url(url: str):
            raise Url2mdExtractionError("boom")

        monkeypatch.setattr("app.services.url_extractor_client.extract_url", fake_extract_url)

        text = await _call(
            mcp_app,
            "ingest_url",
            knowledge_base_id=str(sample_kb.id),
            url="https://example.com/broken",
        )
        assert text == "Error: extraction failed — boom"


# ============================================================================
# Disabled-tool guard
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestToolDisabling:
    async def test_disabled_tool_returns_error(self, mcp_app, monkeypatch):
        monkeypatch.setattr(settings, "MCP_TOOLS_ENABLED", ["rag_query"])
        text = await _call(mcp_app, "list_knowledge_bases")
        assert text == "Error: MCP tool 'list_knowledge_bases' is disabled."

    async def test_db_override_takes_precedence(self, mcp_app, mcp_db, monkeypatch):
        from app.core.system_settings import SystemSettingsManager

        monkeypatch.setattr(settings, "MCP_TOOLS_ENABLED", ["rag_query"])

        async with mcp_db() as db:
            await SystemSettingsManager.save_setting(
                db,
                key="mcp_tools_enabled",
                value=json.dumps(["list_knowledge_bases"]),
                category="mcp",
            )

        text = await _call(mcp_app, "list_knowledge_bases")
        assert text == "No knowledge bases found."
