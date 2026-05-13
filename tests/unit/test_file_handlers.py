"""Unit tests for file handlers."""

import pytest

from app.models.enums import FileType
from app.utils.file_handlers import (
    FileHandlerFactory,
    MarkdownFileHandler,
    PDFFileHandler,
    TextFileHandler,
    process_file,
)


@pytest.mark.unit
class TestTextFileHandler:
    """Test TextFileHandler."""

    def test_can_handle_txt(self):
        """Test handler recognizes .txt files."""
        handler = TextFileHandler()
        assert handler.can_handle(FileType.TXT) is True
        assert handler.can_handle(FileType.MD) is False

    def test_extract_text(self):
        """Test text extraction from .txt file."""
        handler = TextFileHandler()
        content = "Hello, World!\nThis is a test."
        text = handler.extract_text(content, {})
        assert "Hello, World!" in text
        assert "test" in text

    def test_extract_metadata(self):
        """Test metadata extraction from .txt file."""
        handler = TextFileHandler()
        content = "Line 1\nLine 2\nLine 3"
        metadata = handler.extract_metadata(content, "test.txt")

        assert metadata["file_type"] == "txt"
        assert metadata["filename"] == "test.txt"
        assert metadata["line_count"] == 3
        assert "char_count" in metadata
        assert "word_count" in metadata


@pytest.mark.unit
class TestMarkdownFileHandler:
    """Test MarkdownFileHandler."""

    def test_can_handle_md(self):
        """Test handler recognizes .md files."""
        handler = MarkdownFileHandler()
        assert handler.can_handle(FileType.MD) is True
        assert handler.can_handle(FileType.TXT) is False

    def test_extract_text(self, sample_markdown: str):
        """Test text extraction from .md file."""
        handler = MarkdownFileHandler()
        text = handler.extract_text(sample_markdown, {})
        assert "Main Title" in text
        assert "Section 1" in text

    def test_extract_metadata(self, sample_markdown: str):
        """Test metadata extraction from .md file."""
        handler = MarkdownFileHandler()
        metadata = handler.extract_metadata(sample_markdown, "README.md")

        assert metadata["file_type"] == "md"
        assert metadata["filename"] == "README.md"
        assert metadata["heading_count"] > 0
        assert "line_count" in metadata


@pytest.mark.unit
class TestFileHandlerFactory:
    """Test FileHandlerFactory."""

    def test_get_handler_for_txt(self):
        """Test factory returns correct handler for .txt."""
        handler = FileHandlerFactory.get_handler(FileType.TXT)
        assert isinstance(handler, TextFileHandler)

    def test_get_handler_for_md(self):
        """Test factory returns correct handler for .md."""
        handler = FileHandlerFactory.get_handler(FileType.MD)
        assert isinstance(handler, MarkdownFileHandler)

    def test_process_file(self):
        """Test process_file convenience function."""
        content = "# Test\n\nContent here."
        result = process_file(content, "test.md", FileType.MD)

        assert "text" in result
        assert "metadata" in result
        assert result["text"] == content.strip()
        assert result["metadata"]["file_type"] == "md"


@pytest.mark.unit
class TestPDFColumnDetection:
    """Tests for PDFFileHandler column-aware reading order."""

    def test_single_column_returns_none(self):
        """A page where all blocks share a similar x-center is single-column."""
        # Six blocks all roughly aligned: centers ~ 300, no large gap
        items = [
            (10, 50, 550, "block 1"),
            (40, 50, 550, "block 2"),
            (70, 50, 550, "block 3"),
            (100, 50, 550, "block 4"),
            (130, 50, 550, "block 5"),
            (160, 50, 550, "block 6"),
        ]
        assert PDFFileHandler._detect_column_gutter(items, page_width=600) is None

    def test_two_columns_detected(self):
        """Blocks clearly split into left/right groups → gutter at midpoint."""
        # 3 left (x 0..100, center 50), 3 right (x 200..300, center 250)
        items = [
            (10, 0, 100, "L1"),
            (20, 200, 300, "R1"),
            (30, 0, 100, "L2"),
            (40, 200, 300, "R2"),
            (50, 0, 100, "L3"),
            (60, 200, 300, "R3"),
        ]
        gutter = PDFFileHandler._detect_column_gutter(items, page_width=300)
        assert gutter == pytest.approx(150.0)

    def test_too_few_blocks_returns_none(self):
        """Need at least 6 blocks before column detection trusts the signal."""
        items = [
            (10, 0, 100, "L"),
            (20, 200, 300, "R"),
            (30, 0, 100, "L"),
            (40, 200, 300, "R"),
        ]
        assert PDFFileHandler._detect_column_gutter(items, page_width=300) is None

    def test_lopsided_distribution_returns_none(self):
        """Detection requires ≥3 blocks on each side of the gutter."""
        # 5 left, 1 right — does not look like a real 2-column layout
        items = [
            (10, 0, 100, "L1"),
            (20, 0, 100, "L2"),
            (30, 0, 100, "L3"),
            (40, 0, 100, "L4"),
            (50, 0, 100, "L5"),
            (60, 200, 300, "R1"),
        ]
        assert PDFFileHandler._detect_column_gutter(items, page_width=300) is None

    def test_sort_two_columns_reads_left_then_right(self):
        """Multi-column sort produces left column top-to-bottom, then right."""
        # Intentionally interleaved input
        items = [
            (10, 0, 100, "L1"),
            (10, 200, 300, "R1"),
            (50, 0, 100, "L2"),
            (50, 200, 300, "R2"),
        ]
        sorted_items = PDFFileHandler._sort_blocks_by_column(items, gutter_x=150, page_width=300)
        texts = [it[3] for it in sorted_items]
        assert texts == ["L1", "L2", "R1", "R2"]

    def test_sort_spanning_block_breaks_column_flow(self):
        """A wide block crossing the gutter splits the page into bands."""
        # Top: title spans both columns
        # Middle: 2-column body
        # Bottom: footer-style spanning block
        items = [
            (0, 50, 550, "TITLE"),  # spans, wide
            (50, 0, 100, "L1"),
            (50, 200, 300, "R1"),
            (100, 0, 100, "L2"),
            (100, 200, 300, "R2"),
            (200, 50, 550, "FOOTNOTE"),  # spans, wide
        ]
        sorted_items = PDFFileHandler._sort_blocks_by_column(items, gutter_x=150, page_width=600)
        texts = [it[3] for it in sorted_items]
        assert texts == ["TITLE", "L1", "L2", "R1", "R2", "FOOTNOTE"]

    def test_sanitize_chars_preserves_length_for_clean_text(self):
        """Clean ASCII text passes through _sanitize_chars unchanged."""
        text = "Hello, world!\nLine 2\tTab here."
        assert PDFFileHandler._sanitize_chars(text) == text

    def test_sanitize_chars_strips_null_bytes_and_control_chars(self):
        """Null bytes, BEL/VT/etc are removed; \\n and \\t are kept."""
        # \x00 null, \x07 BEL (C0), \x9F (C1) — all should be removed
        # \n (line feed) and \t (tab) — kept
        raw = "hi\x00\x07\x9f\nworld\t!"
        assert PDFFileHandler._sanitize_chars(raw) == "hi\nworld\t!"

    def test_sanitize_chars_does_not_strip_edges(self):
        """Unlike sanitize_text_content, _sanitize_chars preserves leading/trailing whitespace.

        This matters for offset accuracy: a final .strip() would silently
        shift every recorded heading/page position.
        """
        assert PDFFileHandler._sanitize_chars("  hello  ") == "  hello  "

    def test_thin_block_crossing_gutter_is_not_spanning(self):
        """A narrow block that just touches the gutter stays in its column."""
        # Block crosses gutter (x=140..160) but is narrow → assigned by center
        items = [
            (10, 0, 100, "L1"),
            (20, 140, 160, "NARROW"),  # crosses gutter but too thin to be spanning
            (30, 200, 300, "R1"),
            (40, 0, 100, "L2"),
            (50, 200, 300, "R2"),
            (60, 0, 100, "L3"),
        ]
        sorted_items = PDFFileHandler._sort_blocks_by_column(items, gutter_x=150, page_width=300)
        texts = [it[3] for it in sorted_items]
        # NARROW has center at x=150 → falls on right side (>= gutter)
        assert "NARROW" in texts
        # All items present
        assert len(texts) == 6
