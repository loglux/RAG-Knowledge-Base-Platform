"""Unit tests for text chunking service."""

import pytest

from app.services.chunking import (
    Chunk,
    ChunkingService,
    FixedSizeChunking,
    RecursiveChunking,
    SemanticChunking,
    get_chunking_service,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def short_text():
    """Text that fits in a single chunk."""
    return "This is a short text. It fits in one chunk easily."


@pytest.fixture
def long_text():
    """Text long enough to require multiple chunks."""
    return (
        "First sentence of the document. Second sentence follows. Third sentence here. "
        "Fourth sentence continues. Fifth sentence adds more. Sixth sentence contributes. "
        "Seventh sentence keeps going. Eighth sentence still here. Ninth sentence almost done. "
        "Tenth sentence wraps up this paragraph.\n\n"
        "Second paragraph begins here. It also has multiple sentences. More content follows. "
        "Even more content here. This paragraph is also long. It has many sentences. "
        "The sentences keep coming. They just do not stop. Almost done now. Final sentence."
    )


# ============================================================================
# Chunk model
# ============================================================================


@pytest.mark.unit
class TestChunk:
    def test_len(self):
        chunk = Chunk(content="hello world", index=0, start_char=0, end_char=11)
        assert len(chunk) == 11

    def test_char_count(self):
        chunk = Chunk(content="hello world", index=0, start_char=0, end_char=11)
        assert chunk.char_count == 11

    def test_word_count(self):
        chunk = Chunk(content="hello world foo", index=0, start_char=0, end_char=15)
        assert chunk.word_count == 3

    def test_default_metadata_is_empty_dict(self):
        chunk = Chunk(content="text", index=0, start_char=0, end_char=4)
        assert chunk.metadata == {}

    def test_custom_metadata_stored(self):
        meta = {"source": "test.txt", "page": 1}
        chunk = Chunk(content="text", index=0, start_char=0, end_char=4, metadata=meta)
        assert chunk.metadata["source"] == "test.txt"
        assert chunk.metadata["page"] == 1


# ============================================================================
# FixedSizeChunking
# ============================================================================


@pytest.mark.unit
class TestFixedSizeChunking:
    def test_empty_string_returns_empty_list(self):
        strategy = FixedSizeChunking(chunk_size=100, chunk_overlap=10)
        assert strategy.split("") == []

    def test_whitespace_only_returns_empty_list(self):
        strategy = FixedSizeChunking(chunk_size=100, chunk_overlap=10)
        assert strategy.split("   \n\n  ") == []

    def test_short_text_produces_single_chunk(self, short_text):
        strategy = FixedSizeChunking(chunk_size=500, chunk_overlap=50)
        chunks = strategy.split(short_text)
        assert len(chunks) == 1
        assert chunks[0].index == 0
        assert chunks[0].start_char == 0

    def test_long_text_produces_multiple_chunks(self, long_text):
        strategy = FixedSizeChunking(chunk_size=100, chunk_overlap=20)
        chunks = strategy.split(long_text)
        assert len(chunks) > 1

    def test_chunk_content_never_exceeds_chunk_size(self, long_text):
        chunk_size = 150
        strategy = FixedSizeChunking(chunk_size=chunk_size, chunk_overlap=20)
        chunks = strategy.split(long_text)
        for chunk in chunks:
            assert len(chunk.content) <= chunk_size

    def test_chunk_indices_are_sequential(self, long_text):
        strategy = FixedSizeChunking(chunk_size=100, chunk_overlap=20)
        chunks = strategy.split(long_text)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_metadata_attached_to_every_chunk(self, long_text):
        strategy = FixedSizeChunking(chunk_size=100, chunk_overlap=20)
        meta = {"doc_id": "123", "source": "test.md"}
        chunks = strategy.split(long_text, metadata=meta)
        for chunk in chunks:
            assert chunk.metadata["doc_id"] == "123"
            assert chunk.metadata["source"] == "test.md"

    def test_overlap_equal_to_size_raises_value_error(self):
        with pytest.raises(ValueError, match="overlap"):
            FixedSizeChunking(chunk_size=100, chunk_overlap=100)

    def test_overlap_larger_than_size_raises_value_error(self):
        with pytest.raises(ValueError, match="overlap"):
            FixedSizeChunking(chunk_size=100, chunk_overlap=200)

    def test_all_chunks_are_non_empty(self, long_text):
        strategy = FixedSizeChunking(chunk_size=100, chunk_overlap=20)
        chunks = strategy.split(long_text)
        for chunk in chunks:
            assert len(chunk.content.strip()) > 0

    def test_normalizes_multiple_spaces(self):
        strategy = FixedSizeChunking(chunk_size=500, chunk_overlap=50)
        chunks = strategy.split("Hello   world.\t\tThis  is  a  test.")
        assert "   " not in chunks[0].content
        assert "\t" not in chunks[0].content

    def test_normalizes_excessive_newlines(self):
        strategy = FixedSizeChunking(chunk_size=500, chunk_overlap=50)
        chunks = strategy.split("Paragraph one.\n\n\n\n\nParagraph two.")
        assert len(chunks) == 1
        assert "\n\n\n" not in chunks[0].content

    def test_without_sentence_boundary_produces_chunks(self, long_text):
        strategy = FixedSizeChunking(
            chunk_size=100, chunk_overlap=10, respect_sentence_boundary=False
        )
        chunks = strategy.split(long_text)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.content) <= 100

    def test_start_and_end_char_are_set(self, long_text):
        strategy = FixedSizeChunking(chunk_size=100, chunk_overlap=20)
        chunks = strategy.split(long_text)
        for chunk in chunks:
            assert chunk.start_char >= 0
            assert chunk.end_char > chunk.start_char


# ============================================================================
# RecursiveChunking
# ============================================================================


@pytest.mark.unit
class TestRecursiveChunking:
    def test_empty_string_returns_empty_list(self):
        strategy = RecursiveChunking(chunk_size=100, chunk_overlap=10)
        assert strategy.split("") == []

    def test_whitespace_only_returns_empty_list(self):
        strategy = RecursiveChunking(chunk_size=100, chunk_overlap=10)
        assert strategy.split("   ") == []

    def test_short_text_produces_single_chunk(self, short_text):
        strategy = RecursiveChunking(chunk_size=500, chunk_overlap=50)
        chunks = strategy.split(short_text)
        assert len(chunks) == 1

    def test_long_text_produces_multiple_chunks(self, long_text):
        strategy = RecursiveChunking(chunk_size=100, chunk_overlap=20)
        chunks = strategy.split(long_text)
        assert len(chunks) > 1

    def test_chunk_indices_are_sequential(self, long_text):
        strategy = RecursiveChunking(chunk_size=100, chunk_overlap=20)
        chunks = strategy.split(long_text)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_metadata_attached_to_every_chunk(self, long_text):
        strategy = RecursiveChunking(chunk_size=100, chunk_overlap=20)
        meta = {"source": "book.md"}
        chunks = strategy.split(long_text, metadata=meta)
        for chunk in chunks:
            assert chunk.metadata["source"] == "book.md"

    def test_overlap_equal_to_size_raises_value_error(self):
        with pytest.raises(ValueError, match="overlap"):
            RecursiveChunking(chunk_size=100, chunk_overlap=100)

    def test_all_chunks_are_non_empty(self, long_text):
        strategy = RecursiveChunking(chunk_size=100, chunk_overlap=20)
        chunks = strategy.split(long_text)
        for chunk in chunks:
            assert len(chunk.content.strip()) > 0

    def test_paragraph_text_split_into_multiple_chunks(self):
        text = (
            "Paragraph one sentence one. Paragraph one sentence two. Paragraph one sentence three.\n\n"
            "Paragraph two sentence one. Paragraph two sentence two. Paragraph two sentence three."
        )
        strategy = RecursiveChunking(chunk_size=80, chunk_overlap=10)
        chunks = strategy.split(text)
        assert len(chunks) >= 2

    def test_returns_chunk_objects(self, long_text):
        strategy = RecursiveChunking(chunk_size=100, chunk_overlap=20)
        chunks = strategy.split(long_text)
        for chunk in chunks:
            assert isinstance(chunk, Chunk)


# ============================================================================
# ChunkingService
# ============================================================================


@pytest.mark.unit
class TestChunkingService:
    def test_empty_string_raises_value_error(self):
        service = ChunkingService()
        with pytest.raises(ValueError, match="empty"):
            service.chunk_text("")

    def test_whitespace_raises_value_error(self):
        service = ChunkingService()
        with pytest.raises(ValueError, match="empty"):
            service.chunk_text("   ")

    def test_returns_chunk_list(self, long_text):
        service = ChunkingService(strategy=FixedSizeChunking(chunk_size=100, chunk_overlap=20))
        chunks = service.chunk_text(long_text)
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_passes_metadata_to_chunks(self, long_text):
        service = ChunkingService(strategy=FixedSizeChunking(chunk_size=100, chunk_overlap=20))
        meta = {"doc_id": "abc"}
        chunks = service.chunk_text(long_text, metadata=meta)
        for chunk in chunks:
            assert chunk.metadata["doc_id"] == "abc"

    def test_set_strategy_changes_behavior(self, long_text):
        service = ChunkingService(strategy=FixedSizeChunking(chunk_size=400, chunk_overlap=40))
        chunks_large = service.chunk_text(long_text)

        service.set_strategy(FixedSizeChunking(chunk_size=50, chunk_overlap=10))
        chunks_small = service.chunk_text(long_text)

        assert len(chunks_small) > len(chunks_large)

    def test_default_strategy_is_fixed_size(self):
        service = ChunkingService()
        assert isinstance(service.strategy, FixedSizeChunking)


# ============================================================================
# get_chunking_service factory
# ============================================================================


@pytest.mark.unit
class TestGetChunkingService:
    def test_simple_strategy_creates_fixed_size(self):
        service = get_chunking_service(chunk_size=200, chunk_overlap=20, strategy_name="simple")
        assert isinstance(service.strategy, FixedSizeChunking)

    def test_smart_strategy_creates_recursive(self):
        service = get_chunking_service(chunk_size=200, chunk_overlap=20, strategy_name="smart")
        assert isinstance(service.strategy, RecursiveChunking)

    def test_legacy_fixed_size_name(self):
        service = get_chunking_service(chunk_size=200, chunk_overlap=20, strategy_name="fixed_size")
        assert isinstance(service.strategy, FixedSizeChunking)

    def test_legacy_paragraph_name(self):
        service = get_chunking_service(chunk_size=200, chunk_overlap=20, strategy_name="paragraph")
        assert isinstance(service.strategy, RecursiveChunking)

    def test_unknown_strategy_falls_back_to_fixed_size(self):
        service = get_chunking_service(
            chunk_size=200, chunk_overlap=20, strategy_name="unknown_xyz"
        )
        assert isinstance(service.strategy, FixedSizeChunking)

    def test_chunk_size_passed_to_strategy(self):
        service = get_chunking_service(chunk_size=300, chunk_overlap=30, strategy_name="simple")
        assert service.strategy.chunk_size == 300

    def test_chunk_overlap_passed_to_strategy(self):
        service = get_chunking_service(chunk_size=300, chunk_overlap=30, strategy_name="simple")
        assert service.strategy.chunk_overlap == 30

    def test_returns_chunking_service_instance(self):
        service = get_chunking_service(chunk_size=200, chunk_overlap=20, strategy_name="simple")
        assert isinstance(service, ChunkingService)


@pytest.mark.unit
class TestSemanticChunkingContextualDescriptions:
    def test_sync_contextual_descriptions_populated_for_openai_client(self):
        semantic = SemanticChunking.__new__(SemanticChunking)
        semantic.llm_model = "gpt-test"

        class _DummyChoiceMessage:
            content = "Chunk context summary"

        class _DummyChoice:
            message = _DummyChoiceMessage()

        class _DummyResponse:
            choices = [_DummyChoice()]

        class _DummyCompletions:
            @staticmethod
            def create(**kwargs):
                return _DummyResponse()

        class _DummyChat:
            completions = _DummyCompletions()

        class _DummyOpenAIClient:
            chat = _DummyChat()

        semantic.llm_client = _DummyOpenAIClient()

        chunks = [{"content": "Some chunk text", "start_char": 0, "end_char": 15}]
        out = semantic._add_contextual_descriptions_sync(chunks, "Whole document text")

        assert out[0]["contextual_description"] == "Chunk context summary"
