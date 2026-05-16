"""Unit tests for chat → eval promotion plumbing.

Focus on the pure helpers — full ORM round-trips are covered by the
end-to-end rating endpoint tests; here we make sure the source-pointer
extraction is robust against malformed payloads, since promoted samples
come straight from chat traffic.
"""

import json

import pytest

from app.services.feedback_promotion import _first_source_pointer


@pytest.mark.unit
class TestFirstSourcePointer:
    """_first_source_pointer must never raise on user-shaped input."""

    def test_none_input_returns_all_none(self):
        assert _first_source_pointer(None) == (None, None, None)

    def test_empty_string_returns_all_none(self):
        assert _first_source_pointer("") == (None, None, None)

    def test_malformed_json_returns_all_none(self):
        assert _first_source_pointer("{not json") == (None, None, None)

    def test_non_list_payload_returns_all_none(self):
        assert _first_source_pointer(json.dumps({"sources": []})) == (None, None, None)

    def test_empty_list_returns_all_none(self):
        assert _first_source_pointer("[]") == (None, None, None)

    def test_well_formed_chunk(self):
        sources = [
            {
                "document_id": "fea29ac4-e52e-45e7-b236-656282fc5771",
                "chunk_index": 15,
                "text": "Question 6 – 20 marks ...",
            }
        ]
        doc_id, chunk_idx, span = _first_source_pointer(json.dumps(sources))
        assert str(doc_id) == "fea29ac4-e52e-45e7-b236-656282fc5771"
        assert chunk_idx == 15
        assert span.startswith("Question 6")

    def test_falls_back_to_content_field(self):
        sources = [{"document_id": "fea29ac4-e52e-45e7-b236-656282fc5771", "content": "alt body"}]
        _, _, span = _first_source_pointer(json.dumps(sources))
        assert span == "alt body"

    def test_invalid_document_id_does_not_break_chunk_idx(self):
        sources = [{"document_id": "not-a-uuid", "chunk_index": 7, "text": "..."}]
        doc_id, chunk_idx, _ = _first_source_pointer(json.dumps(sources))
        assert doc_id is None
        assert chunk_idx == 7

    def test_string_chunk_index_is_coerced(self):
        sources = [{"document_id": None, "chunk_index": "12", "text": "..."}]
        _, chunk_idx, _ = _first_source_pointer(json.dumps(sources))
        assert chunk_idx == 12

    def test_non_dict_first_item_returns_all_none(self):
        assert _first_source_pointer(json.dumps(["just a string"])) == (None, None, None)

    def test_text_with_non_string_type_is_dropped(self):
        sources = [{"document_id": None, "chunk_index": 1, "text": {"nested": "obj"}}]
        _, _, span = _first_source_pointer(json.dumps(sources))
        assert span is None
