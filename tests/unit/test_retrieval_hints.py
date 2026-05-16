"""Unit tests for the retrieval UX-hint generator."""

from dataclasses import dataclass
from typing import Optional

import pytest

from app.services.retrieval_hints import (
    COVER_CHUNK_INDEX_CEILING,
    LOW_CONFIDENCE_TOP1_THRESHOLD,
    build_hint_for_response,
)


@dataclass
class _StubChunk:
    """Minimal stand-in for RetrievedChunk used in hint generation."""

    score: float
    chunk_index: int
    document_id: Optional[str] = "doc-a"


@pytest.mark.unit
class TestBuildHintForResponse:
    """build_hint_for_response should fire only when retrieval looks suspicious."""

    def test_no_hint_for_paraphrase_query(self):
        # Even with low scores, a non-identifier query gets no hint.
        chunks = [_StubChunk(score=0.3, chunk_index=0)]
        assert build_hint_for_response("how does antifragility work", chunks) is None

    def test_no_hint_when_identifier_query_has_strong_top1(self):
        chunks = [_StubChunk(score=0.85, chunk_index=15)]
        assert build_hint_for_response("Question 6 from EMA", chunks) is None

    def test_hint_when_identifier_query_has_low_top1(self):
        chunks = [_StubChunk(score=0.5, chunk_index=15)]
        hint = build_hint_for_response("Question 6 from EMA", chunks)
        assert hint is not None
        assert hint.type == "identifier_low_confidence"
        assert "Question 6" in hint.message
        # Should offer at least the two canonical actions
        actions = [s["action"] for s in hint.suggestions]
        assert "scope_to_document" in actions
        assert "raise_top_k" in actions

    def test_hint_when_identifier_query_dominated_by_covers(self):
        """Even with a top-1 score above threshold, cover-dominated top-K triggers a hint."""
        chunks = [
            _StubChunk(score=0.95, chunk_index=0, document_id="doc-a"),
            _StubChunk(score=0.90, chunk_index=1, document_id="doc-b"),
            _StubChunk(score=0.85, chunk_index=0, document_id="doc-c"),
            _StubChunk(score=0.30, chunk_index=18, document_id="doc-a"),
        ]
        hint = build_hint_for_response("Open Question 6 from EMA", chunks)
        assert hint is not None
        assert hint.type == "identifier_low_confidence"

    def test_no_hint_when_covers_all_from_one_document(self):
        """Cover dominance requires multiple documents — single-doc front-matter is fine."""
        chunks = [
            _StubChunk(score=0.95, chunk_index=0, document_id="doc-a"),
            _StubChunk(score=0.90, chunk_index=1, document_id="doc-a"),
            _StubChunk(score=0.85, chunk_index=2, document_id="doc-a"),
        ]
        assert build_hint_for_response("Question 6 from EMA", chunks) is None

    def test_no_hint_when_no_chunks(self):
        assert build_hint_for_response("Question 6", []) is None

    def test_threshold_is_documented_value(self):
        # Anchors the magic numbers so future changes break the test and
        # force the author to update the docs / roadmap together.
        assert LOW_CONFIDENCE_TOP1_THRESHOLD == 0.7
        assert COVER_CHUNK_INDEX_CEILING == 2
