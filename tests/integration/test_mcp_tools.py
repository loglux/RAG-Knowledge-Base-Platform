"""Integration tests for the FastMCP tool registry in app.mcp.server.

These tools call get_db_session() directly instead of going through FastAPI's
Depends(get_db), so the test_client dependency-override pattern used elsewhere
doesn't apply here — instead we point app.db.session's global session factory
at the test engine (see the mcp_db fixture below).
"""

import asyncio
import base64
import json
import re
import time
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.db.session as db_session_module
from app.config import Settings, settings
from app.mcp.server import MCP_TOOL_NAMES, build_mcp_app
from app.models.database import Document, KnowledgeBase
from app.services.upload_signing import sign_upload


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
# update_knowledge_base / delete_knowledge_base
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestUpdateKnowledgeBase:
    async def test_missing_kb(self, mcp_app):
        text = await _call(
            mcp_app, "update_knowledge_base", knowledge_base_id=str(uuid4()), name="New Name"
        )
        assert text.startswith("Error:")
        assert "not found" in text

    async def test_no_fields_provided(self, mcp_app, sample_kb: KnowledgeBase):
        text = await _call(mcp_app, "update_knowledge_base", knowledge_base_id=str(sample_kb.id))
        assert text == "Error: at least one field to update must be provided."

    async def test_updates_name_and_description(self, mcp_app, sample_kb: KnowledgeBase, mcp_db):
        text = await _call(
            mcp_app,
            "update_knowledge_base",
            knowledge_base_id=str(sample_kb.id),
            name="Renamed KB",
            description="New description",
        )
        assert text.startswith("Updated knowledge base 'Renamed KB'")

        async with mcp_db() as db:
            result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == sample_kb.id))
            kb = result.scalar_one()
            assert kb.name == "Renamed KB"
            assert kb.description == "New description"


@pytest.mark.integration
@pytest.mark.asyncio
class TestDeleteKnowledgeBase:
    async def test_missing_kb(self, mcp_app):
        text = await _call(mcp_app, "delete_knowledge_base", knowledge_base_id=str(uuid4()))
        assert text.startswith("Error:")
        assert "not found" in text

    async def test_soft_deletes_kb_and_documents(
        self, mcp_app, sample_kb: KnowledgeBase, sample_document: Document, mcp_db
    ):
        text = await _call(mcp_app, "delete_knowledge_base", knowledge_base_id=str(sample_kb.id))
        assert text == f"Deleted knowledge base {sample_kb.id}."

        async with mcp_db() as db:
            kb_result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == sample_kb.id)
            )
            kb = kb_result.scalar_one()
            assert kb.is_deleted is True

            doc_result = await db.execute(select(Document).where(Document.id == sample_document.id))
            doc = doc_result.scalar_one()
            assert doc.is_deleted is True

        # Now invisible to the read-only tools too.
        listing = await _call(mcp_app, "list_knowledge_bases")
        assert str(sample_kb.id) not in listing


# ============================================================================
# delete_document
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestDeleteDocument:
    async def test_missing_document(self, mcp_app):
        text = await _call(mcp_app, "delete_document", document_id=str(uuid4()))
        assert text.startswith("Error:")
        assert "not found" in text

    async def test_soft_deletes_document_and_updates_kb_count(
        self, mcp_app, sample_kb: KnowledgeBase, sample_document: Document, mcp_db
    ):
        text = await _call(mcp_app, "delete_document", document_id=str(sample_document.id))
        assert text == f"Deleted document {sample_document.id}."

        async with mcp_db() as db:
            doc_result = await db.execute(select(Document).where(Document.id == sample_document.id))
            doc = doc_result.scalar_one()
            assert doc.is_deleted is True

            kb_result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == sample_kb.id)
            )
            kb = kb_result.scalar_one()
            assert kb.document_count == 0

        listing = await _call(mcp_app, "list_documents", knowledge_base_id=str(sample_kb.id))
        assert listing == "No documents found for this knowledge base."


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
# upload_document
# ============================================================================


def _make_test_pdf_base64(text: str = "Hello PDF World") -> str:
    import fitz

    # PDFFileHandler rejects extractions under 100 chars as likely-scanned, so
    # pad short marker text with enough filler to clear that threshold.
    body = f"{text}. " + "Lorem ipsum dolor sit amet padding text. " * 4

    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(72, 72, 500, 700), body)
    data = doc.tobytes()
    doc.close()
    return base64.b64encode(data).decode("ascii")


@pytest.mark.integration
@pytest.mark.asyncio
class TestUploadDocument:
    async def test_missing_kb(self, mcp_app):
        text = await _call(
            mcp_app,
            "upload_document",
            knowledge_base_id=str(uuid4()),
            filename="report.pdf",
            content_base64=_make_test_pdf_base64(),
        )
        assert text.startswith("Error:")
        assert "not found" in text

    async def test_invalid_base64(self, mcp_app, sample_kb: KnowledgeBase):
        text = await _call(
            mcp_app,
            "upload_document",
            knowledge_base_id=str(sample_kb.id),
            filename="report.pdf",
            content_base64="not-valid-base64!!!",
        )
        assert text == "Error: content_base64 is not valid base64."

    async def test_unsupported_extension(self, mcp_app, sample_kb: KnowledgeBase):
        text = await _call(
            mcp_app,
            "upload_document",
            knowledge_base_id=str(sample_kb.id),
            filename="archive.zip",
            content_base64=base64.b64encode(b"whatever").decode("ascii"),
        )
        assert text.startswith("Error:")
        assert "Unsupported file type" in text

    async def test_uploads_pdf_and_extracts_structure(
        self, mcp_app, sample_kb: KnowledgeBase, mcp_db
    ):
        text = await _call(
            mcp_app,
            "upload_document",
            knowledge_base_id=str(sample_kb.id),
            filename="report.pdf",
            content_base64=_make_test_pdf_base64("Hello PDF World"),
        )
        assert text.startswith("Uploaded 'report.pdf'")
        await _drain_background_tasks(mcp_app)

        async with mcp_db() as db:
            result = await db.execute(
                select(Document).where(Document.knowledge_base_id == sample_kb.id)
            )
            doc = result.scalar_one()
            assert doc.file_type == "pdf"
            assert "Hello PDF World" in doc.content
            # doc.file_path (saved to /app/uploads for reprocess/download) is
            # environment-dependent — not writable outside the container, so
            # it's not asserted here; create_document already logs and
            # swallows that failure without affecting ingestion.

    async def test_duplicate_content_rejected(self, mcp_app, sample_kb: KnowledgeBase):
        content_b64 = _make_test_pdf_base64("Duplicate check")
        first = await _call(
            mcp_app,
            "upload_document",
            knowledge_base_id=str(sample_kb.id),
            filename="a.pdf",
            content_base64=content_b64,
        )
        assert first.startswith("Uploaded")
        await _drain_background_tasks(mcp_app)

        second = await _call(
            mcp_app,
            "upload_document",
            knowledge_base_id=str(sample_kb.id),
            filename="b.pdf",
            content_base64=content_b64,
        )
        assert second.startswith("Error:")
        assert "already exists" in second

    async def test_neither_content_nor_path_provided(self, mcp_app, sample_kb: KnowledgeBase):
        text = await _call(
            mcp_app,
            "upload_document",
            knowledge_base_id=str(sample_kb.id),
            filename="report.pdf",
        )
        assert text == "Error: provide exactly one of content_base64 or path."

    async def test_both_content_and_path_provided(self, mcp_app, sample_kb: KnowledgeBase):
        text = await _call(
            mcp_app,
            "upload_document",
            knowledge_base_id=str(sample_kb.id),
            filename="report.pdf",
            content_base64=_make_test_pdf_base64(),
            path="report.pdf",
        )
        assert text == "Error: provide exactly one of content_base64 or path."


@pytest.mark.integration
@pytest.mark.asyncio
class TestUploadDocumentViaPath:
    @pytest.fixture
    def inbox_dir(self, tmp_path, monkeypatch):
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        monkeypatch.setattr("app.mcp.server.UPLOAD_INBOX_DIR", inbox)
        return inbox

    async def test_file_not_found(self, mcp_app, sample_kb: KnowledgeBase, inbox_dir):
        text = await _call(
            mcp_app,
            "upload_document",
            knowledge_base_id=str(sample_kb.id),
            path="missing.pdf",
        )
        assert text.startswith("Error:")
        assert "not found" in text

    async def test_path_traversal_rejected(self, mcp_app, sample_kb: KnowledgeBase, inbox_dir):
        outside_file = inbox_dir.parent / "secret.txt"
        outside_file.write_text("should not be readable")

        text = await _call(
            mcp_app,
            "upload_document",
            knowledge_base_id=str(sample_kb.id),
            path="../secret.txt",
        )
        assert text == "Error: path must stay within the uploads/inbox directory."

    async def test_uploads_from_inbox(self, mcp_app, sample_kb: KnowledgeBase, mcp_db, inbox_dir):
        pdf_bytes = base64.b64decode(_make_test_pdf_base64("From inbox"))
        (inbox_dir / "report.pdf").write_bytes(pdf_bytes)

        text = await _call(
            mcp_app,
            "upload_document",
            knowledge_base_id=str(sample_kb.id),
            path="report.pdf",
        )
        assert text.startswith("Uploaded 'report.pdf'")
        await _drain_background_tasks(mcp_app)

        async with mcp_db() as db:
            result = await db.execute(
                select(Document).where(Document.knowledge_base_id == sample_kb.id)
            )
            doc = result.scalar_one()
            assert doc.file_type == "pdf"
            assert "From inbox" in doc.content

    async def test_filename_defaults_to_path_basename(
        self, mcp_app, sample_kb: KnowledgeBase, mcp_db, inbox_dir
    ):
        pdf_bytes = base64.b64decode(_make_test_pdf_base64("Nested file"))
        subdir = inbox_dir / "sub"
        subdir.mkdir()
        (subdir / "nested.pdf").write_bytes(pdf_bytes)

        text = await _call(
            mcp_app,
            "upload_document",
            knowledge_base_id=str(sample_kb.id),
            path="sub/nested.pdf",
        )
        assert text.startswith("Uploaded 'nested.pdf'")


# ============================================================================
# create_upload_url + presigned upload consumption
# ============================================================================


def _extract_upload_path(text: str) -> str:
    match = re.search(r"(/api/v1/uploads/\S+)", text)
    assert match, f"no upload URL found in: {text}"
    return match.group(1)


@pytest.mark.integration
@pytest.mark.asyncio
class TestCreateUploadUrl:
    async def test_missing_kb(self, mcp_app):
        text = await _call(
            mcp_app,
            "create_upload_url",
            knowledge_base_id=str(uuid4()),
            filename="report.pdf",
        )
        assert text.startswith("Error:")
        assert "not found" in text

    async def test_unsupported_extension(self, mcp_app, sample_kb: KnowledgeBase):
        text = await _call(
            mcp_app,
            "create_upload_url",
            knowledge_base_id=str(sample_kb.id),
            filename="archive.zip",
        )
        assert text.startswith("Error:")
        assert "Unsupported file type" in text

    async def test_generates_valid_signed_url(self, mcp_app, sample_kb: KnowledgeBase):
        text = await _call(
            mcp_app,
            "create_upload_url",
            knowledge_base_id=str(sample_kb.id),
            filename="report.pdf",
        )
        assert text.startswith("Upload URL (valid 5 min, single use, max")
        assert "curl -X PUT -T 'report.pdf'" in text

        path = _extract_upload_path(text)
        qs = parse_qs(urlparse(path).query)
        assert qs["kb_id"][0] == str(sample_kb.id)
        assert qs["filename"][0] == "report.pdf"
        assert "expires" in qs
        assert "sig" in qs


@pytest.mark.integration
@pytest.mark.asyncio
class TestConsumeUploadUrl:
    async def test_wrong_signature_rejected(self, mcp_app, sample_kb: KnowledgeBase, test_client):
        text = await _call(
            mcp_app,
            "create_upload_url",
            knowledge_base_id=str(sample_kb.id),
            filename="report.pdf",
        )
        path = _extract_upload_path(text)
        tampered = re.sub(r"sig=[0-9a-f]+", "sig=deadbeef", path)

        response = await test_client.put(tampered, content=b"whatever")
        assert response.status_code == 403

    async def test_expired_url_rejected(self, mcp_app, sample_kb: KnowledgeBase, test_client):
        upload_id = "expired-test-id"
        expires = int(time.time()) - 10
        sig = sign_upload(upload_id, str(sample_kb.id), "report.pdf", expires)

        response = await test_client.put(
            f"/api/v1/uploads/{upload_id}"
            f"?kb_id={sample_kb.id}&filename=report.pdf&expires={expires}&sig={sig}",
            content=b"whatever",
        )
        assert response.status_code == 410

    async def test_successful_upload_and_replay_rejected(
        self, mcp_app, sample_kb: KnowledgeBase, test_client, mcp_db
    ):
        text = await _call(
            mcp_app,
            "create_upload_url",
            knowledge_base_id=str(sample_kb.id),
            filename="report.pdf",
        )
        path = _extract_upload_path(text)
        pdf_bytes = base64.b64decode(_make_test_pdf_base64("Presigned upload works"))

        response = await test_client.put(path, content=pdf_bytes)
        assert response.status_code == 200
        payload = response.json()
        assert payload["filename"] == "report.pdf"

        async with mcp_db() as db:
            result = await db.execute(
                select(Document).where(Document.knowledge_base_id == sample_kb.id)
            )
            doc = result.scalar_one()
            assert doc.file_type == "pdf"
            assert str(doc.id) == payload["document_id"]

        # Replay: the same (still-unexpired) URL must not work twice.
        replay = await test_client.put(path, content=pdf_bytes)
        assert replay.status_code == 409


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
