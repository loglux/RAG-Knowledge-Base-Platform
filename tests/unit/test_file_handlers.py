"""Unit tests for file handlers."""

import pytest

from app.models.enums import FileType
from app.utils.file_handlers import (
    FileHandlerFactory,
    MarkdownFileHandler,
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
