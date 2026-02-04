"""File type handlers for document processing."""
from typing import Dict, Any, Union
from pathlib import Path
from xml.etree import ElementTree
import io

from docx import Document as DocxDocument

from app.models.enums import FileType
from app.utils.logger import get_logger
from app.utils.validators import sanitize_text_content

logger = get_logger(__name__)


class FileHandler:
    """Base class for file handlers."""

    def can_handle(self, file_type: FileType) -> bool:
        """Check if this handler can process the given file type."""
        raise NotImplementedError

    def extract_text(self, content: Union[str, bytes], metadata: Dict[str, Any]) -> str:
        """Extract text content from file."""
        raise NotImplementedError

    def extract_metadata(self, content: Union[str, bytes], filename: str) -> Dict[str, Any]:
        """Extract metadata from file."""
        raise NotImplementedError


class TextFileHandler(FileHandler):
    """Handler for plain text files (.txt)."""

    def can_handle(self, file_type: FileType) -> bool:
        """Check if this is a text file."""
        return file_type == FileType.TXT

    def extract_text(self, content: Union[str, bytes], metadata: Dict[str, Any]) -> str:
        """
        Extract text from plain text file.

        For .txt files, content is already text, just sanitize it.
        """
        logger.debug("Extracting text from .txt file")
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        return sanitize_text_content(content)

    def extract_metadata(self, content: Union[str, bytes], filename: str) -> Dict[str, Any]:
        """
        Extract metadata from text file.

        Returns basic metadata like line count, character count.
        """
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        lines = content.split('\n')
        return {
            "file_type": "txt",
            "filename": filename,
            "line_count": len(lines),
            "char_count": len(content),
            "word_count": len(content.split()),
        }


class MarkdownFileHandler(FileHandler):
    """Handler for Markdown files (.md)."""

    def can_handle(self, file_type: FileType) -> bool:
        """Check if this is a markdown file."""
        return file_type == FileType.MD

    def extract_text(self, content: Union[str, bytes], metadata: Dict[str, Any]) -> str:
        """
        Extract text from markdown file.

        For MVP: Keep markdown as-is for better context preservation.
        Future: Option to strip markdown syntax or convert to plain text.
        """
        logger.debug("Extracting text from .md file")
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        return sanitize_text_content(content)

    def extract_metadata(self, content: Union[str, bytes], filename: str) -> Dict[str, Any]:
        """
        Extract metadata from markdown file.

        Includes markdown-specific metadata like heading count.
        """
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        lines = content.split('\n')

        # Count headings
        heading_count = sum(1 for line in lines if line.strip().startswith('#'))

        # Check for frontmatter (YAML between --- markers)
        has_frontmatter = content.strip().startswith('---')

        return {
            "file_type": "md",
            "filename": filename,
            "line_count": len(lines),
            "char_count": len(content),
            "word_count": len(content.split()),
            "heading_count": heading_count,
            "has_frontmatter": has_frontmatter,
        }


class FB2FileHandler(FileHandler):
    """Handler for FB2 (FictionBook 2.0) files."""

    def can_handle(self, file_type: FileType) -> bool:
        return file_type == FileType.FB2

    def extract_text(self, content: Union[str, bytes], metadata: Dict[str, Any]) -> str:
        logger.debug("Extracting text from .fb2 file")
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            # If XML is invalid, fall back to raw text
            return sanitize_text_content(content)

        # Collect text from body
        texts = []
        for node in root.iter():
            if node.tag.endswith("body"):
                texts.append(" ".join(node.itertext()))

        if not texts:
            texts.append(" ".join(root.itertext()))

        return sanitize_text_content("\n\n".join(texts))

    def extract_metadata(self, content: Union[str, bytes], filename: str) -> Dict[str, Any]:
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            return {
                "file_type": "fb2",
                "filename": filename,
                "char_count": len(content),
                "word_count": len(content.split()),
            }

        title = None
        author = None

        for node in root.iter():
            if node.tag.endswith("book-title") and node.text:
                title = node.text.strip()
                break

        for node in root.iter():
            if node.tag.endswith("author"):
                parts = []
                for child in node:
                    if child.tag.endswith("first-name") and child.text:
                        parts.append(child.text.strip())
                    if child.tag.endswith("last-name") and child.text:
                        parts.append(child.text.strip())
                if parts:
                    author = " ".join(parts)
                    break

        return {
            "file_type": "fb2",
            "filename": filename,
            "title": title,
            "author": author,
            "char_count": len(content),
            "word_count": len(content.split()),
        }


class DocxFileHandler(FileHandler):
    """Handler for DOCX files."""

    def can_handle(self, file_type: FileType) -> bool:
        return file_type == FileType.DOCX

    def _load_document(self, content: Union[str, bytes]) -> DocxDocument:
        if isinstance(content, str):
            content = content.encode("utf-8")
        return DocxDocument(io.BytesIO(content))

    def extract_text(self, content: Union[str, bytes], metadata: Dict[str, Any]) -> str:
        logger.debug("Extracting text from .docx file")
        doc = self._load_document(content)
        texts = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    if cell_text:
                        texts.append(cell_text)
        return sanitize_text_content("\n\n".join(texts))

    def extract_metadata(self, content: Union[str, bytes], filename: str) -> Dict[str, Any]:
        doc = self._load_document(content)
        paragraph_count = len(doc.paragraphs)
        table_count = len(doc.tables)
        text = "\n".join(p.text for p in doc.paragraphs if p.text)
        return {
            "file_type": "docx",
            "filename": filename,
            "paragraph_count": paragraph_count,
            "table_count": table_count,
            "char_count": len(text),
            "word_count": len(text.split()),
        }


class FileHandlerFactory:
    """
    Factory for creating appropriate file handlers.

    Usage:
        handler = FileHandlerFactory.get_handler(FileType.MD)
        text = handler.extract_text(content, {})
    """

    _handlers = [
        TextFileHandler(),
        MarkdownFileHandler(),
        FB2FileHandler(),
        DocxFileHandler(),
    ]

    @classmethod
    def get_handler(cls, file_type: FileType) -> FileHandler:
        """
        Get appropriate handler for file type.

        Args:
            file_type: Type of file to handle

        Returns:
            FileHandler instance

        Raises:
            ValueError: If no handler found for file type
        """
        for handler in cls._handlers:
            if handler.can_handle(file_type):
                return handler

        raise ValueError(f"No handler found for file type: {file_type}")

    @classmethod
    def register_handler(cls, handler: FileHandler) -> None:
        """
        Register a new file handler.

        Useful for adding handlers for new file types in later phases.

        Args:
            handler: FileHandler instance to register
        """
        cls._handlers.append(handler)
        logger.info(f"Registered file handler: {handler.__class__.__name__}")


def process_file(content: Union[str, bytes], filename: str, file_type: FileType) -> Dict[str, Any]:
    """
    Process a file and extract text and metadata.

    Convenience function that uses FileHandlerFactory.

    Args:
        content: File content as string
        filename: Name of the file
        file_type: Type of the file

    Returns:
        Dictionary with 'text' and 'metadata' keys

    Example:
        >>> result = process_file(content, "test.md", FileType.MD)
        >>> print(result['text'])
        >>> print(result['metadata'])
    """
    handler = FileHandlerFactory.get_handler(file_type)

    # Extract metadata first
    metadata = handler.extract_metadata(content, filename)

    # Extract text
    text = handler.extract_text(content, metadata)

    return {
        "text": text,
        "metadata": metadata,
    }
