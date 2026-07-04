"""Unit tests for DocumentProcessor._build_payloads structural metadata.

Regression coverage for the markdown heading_map gap: markdown documents
never go through FileHandlerFactory.extract_all() (that path is DOCX/FB2/PDF
only), so document.heading_map_json was never persisted for them — the UI
"Structure" toggle and document preview always showed nothing for markdown
documents, even though the retrieval payloads themselves carried correct
section_heading/section_path per chunk.
"""

from unittest.mock import MagicMock

import pytest

from app.models.database import Document, KnowledgeBase
from app.models.enums import FileType
from app.services.chunking import Chunk
from app.services.document_processor import DocumentProcessor

MARKDOWN_CONTENT = """# Title

Intro text.

## Section One

Some content in section one.

### Subsection

Deeper content.

## Section Two

More content here.
"""


@pytest.fixture
def processor():
    return DocumentProcessor(
        vector_store=MagicMock(),
        lexical_store=MagicMock(),
        chunking_service=MagicMock(),
    )


@pytest.fixture
def md_document():
    return Document(
        filename="test.md",
        file_type=FileType.MD,
        content=MARKDOWN_CONTENT,
        content_hash="deadbeef",
        file_size=len(MARKDOWN_CONTENT.encode()),
    )


@pytest.fixture
def kb():
    return KnowledgeBase(name="KB", collection_name="test_collection")


def _chunk_at(pos: int, content: str = "chunk text") -> Chunk:
    return Chunk(content=content, index=0, start_char=pos, end_char=pos + len(content))


class TestMarkdownHeadingMapPersistence:
    def test_persists_heading_map_json_for_markdown(self, processor, md_document, kb):
        assert md_document.heading_map_json is None

        chunks = [_chunk_at(MARKDOWN_CONTENT.index("Deeper content"))]
        processor._build_payloads(chunks, md_document, kb)

        assert md_document.heading_map_json is not None
        import json

        headings = json.loads(md_document.heading_map_json)
        assert [h["text"] for h in headings] == [
            "Title",
            "Section One",
            "Subsection",
            "Section Two",
        ]

    def test_chunk_payload_carries_section_metadata(self, processor, md_document, kb):
        chunks = [_chunk_at(MARKDOWN_CONTENT.index("Deeper content"))]
        payloads = processor._build_payloads(chunks, md_document, kb)

        assert payloads[0]["section_heading"] == "Subsection"
        assert payloads[0]["section_path"] == "Title > Section One > Subsection"
        assert payloads[0]["section_level"] == 3

    def test_no_headings_clears_stale_heading_map_json(self, processor, kb):
        doc = Document(
            filename="plain.md",
            file_type=FileType.MD,
            content="just plain text, no headings",
            content_hash="cafebabe",
            file_size=10,
            heading_map_json='[{"pos": 0, "level": 1, "text": "stale"}]',
        )
        chunks = [_chunk_at(0, "just plain text")]
        processor._build_payloads(chunks, doc, kb)

        assert doc.heading_map_json is None
