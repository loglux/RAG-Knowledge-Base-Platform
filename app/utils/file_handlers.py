"""File type handlers for document processing."""

import io
from typing import Any, Dict, List, Union
from xml.etree import ElementTree

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
        lines = content.split("\n")
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
        lines = content.split("\n")

        # Count headings
        heading_count = sum(1 for line in lines if line.strip().startswith("#"))

        # Check for frontmatter (YAML between --- markers)
        has_frontmatter = content.strip().startswith("---")

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

    @staticmethod
    def _parse_body(body_node) -> List[Dict[str, Any]]:
        """Parse an FB2 <body> element into structured text segments.

        Recursively walks sections, extracting titles and paragraphs while
        tracking nesting depth for heading level attribution.

        Returns a list of dicts:
            text       (str)  – stripped text content
            is_heading (bool) – True for <title> elements inside <section>
            level      (int)  – 1-6 nesting depth (1 = top-level section)
        """
        segments: List[Dict[str, Any]] = []

        def _get_node_text(node) -> str:
            return " ".join(t.strip() for t in node.itertext() if t.strip())

        def _process(node, section_depth: int) -> None:
            local = node.tag.split("}")[-1] if "}" in node.tag else node.tag

            if local == "section":
                for child in node:
                    _process(child, section_depth + 1)
            elif local == "title":
                text = _get_node_text(node)
                if text:
                    segments.append(
                        {"text": text, "is_heading": True, "level": max(1, section_depth)}
                    )
            elif local in (
                "p",
                "v",
                "stanza",
                "subtitle",
                "text-author",
                "date",
                "epigraph",
                "cite",
                "annotation",
                "poem",
            ):
                text = _get_node_text(node)
                if text:
                    segments.append({"text": text, "is_heading": False, "level": 0})
            # image, binary, table, etc. — silently skipped (no meaningful text)

        for child in body_node:
            _process(child, 0)

        return segments

    def extract_text(self, content: Union[str, bytes], metadata: Dict[str, Any]) -> str:
        logger.debug("Extracting text from .fb2 file")
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            return sanitize_text_content(content)

        parts: List[str] = []
        for node in root.iter():
            if node.tag.endswith("body"):
                parts.extend(seg["text"] for seg in self._parse_body(node))

        if not parts:
            # Fallback: dump all text from document
            parts.append(" ".join(t for t in root.itertext() if t.strip()))

        return sanitize_text_content("\n\n".join(parts))

    def extract_heading_map(self, content: Union[str, bytes]) -> List[Dict[str, Any]]:
        """Extract heading positions from an FB2 file for structural metadata indexing.

        Uses the same _parse_body traversal as extract_text() so that character
        positions match offsets in the stored document.content string.

        Returns a list of dicts with keys:
            pos   (int)  – character offset in the extracted text
            level (int)  – heading level 1-6 (section nesting depth)
            text  (str)  – heading text
        sorted by position.
        """
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            return []

        all_segments: List[Dict[str, Any]] = []
        for node in root.iter():
            if node.tag.endswith("body"):
                all_segments.extend(self._parse_body(node))

        if not all_segments:
            return []

        headings: List[Dict[str, Any]] = []
        current_pos = 0
        for seg in all_segments:
            if seg["is_heading"] and 1 <= seg["level"] <= 6:
                headings.append({"pos": current_pos, "level": seg["level"], "text": seg["text"]})
            # Each segment contributes len(text) + 2 chars ("\n\n" separator)
            current_pos += len(seg["text"]) + 2

        return headings

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

    def extract_heading_map(self, content: Union[str, bytes]) -> List[Dict[str, Any]]:
        """Extract heading positions from a DOCX file for structural metadata indexing.

        Simulates the same paragraph-joining logic as extract_text() to produce
        character positions that match the stored document.content string.

        Returns a list of dicts with keys:
            pos   (int)  – character offset in the extracted text
            level (int)  – heading level 1-6
            text  (str)  – heading text
        sorted by position.
        """
        doc = self._load_document(content)
        headings: List[Dict[str, Any]] = []
        current_pos = 0

        for p in doc.paragraphs:
            text = p.text
            if not text or not text.strip():
                continue

            style_name = p.style.name if p.style else ""
            if style_name.startswith("Heading "):
                try:
                    level = int(style_name.split(" ")[1])
                    if 1 <= level <= 6:
                        headings.append({"pos": current_pos, "level": level, "text": text.strip()})
                except (ValueError, IndexError):
                    pass

            # Each kept paragraph contributes len(text) + 2 chars ("\n\n" separator)
            current_pos += len(text) + 2

        return headings


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
