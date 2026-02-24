"""File type handlers for document processing."""

import io
from typing import Any, Dict, List, Optional, Union
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
    def _parse_xml(content: str):
        """Parse FB2 XML with lxml recovery fallback.

        Tries stdlib ElementTree first (strict); if that fails, falls back to
        lxml with recover=True which silently fixes mismatched tags and similar
        structural errors common in downloaded FB2 files.
        """
        try:
            return ElementTree.fromstring(content)
        except ElementTree.ParseError:
            pass
        try:
            from lxml import etree

            root_lxml = etree.fromstring(
                content.encode("utf-8") if isinstance(content, str) else content,
                parser=etree.XMLParser(recover=True, encoding="utf-8"),
            )
            # Convert lxml tree to stdlib ElementTree via serialization
            reparsed = ElementTree.fromstring(etree.tostring(root_lxml))
            return reparsed
        except Exception:
            return None

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
        root = self._parse_xml(content)
        if root is None:
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
        root = self._parse_xml(content)
        if root is None:
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
        root = self._parse_xml(content)
        if root is None:
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


class PDFFileHandler(FileHandler):
    """Handler for PDF files (.pdf).

    Extracts text from text-based PDFs using PyMuPDF.
    Scanned (image-only) PDFs are detected and rejected with a clear error.
    Heading detection uses font-size heuristics: the dominant font size is
    treated as body text; larger sizes are ranked into heading levels 1-6.
    """

    def can_handle(self, file_type: FileType) -> bool:
        return file_type == FileType.PDF

    @staticmethod
    def _to_bytes(content: Union[str, bytes]) -> bytes:
        if isinstance(content, str):
            # Should not happen for PDFs, but guard anyway
            return content.encode("utf-8")
        return content

    @staticmethod
    def _extract_footer_page_number(page) -> Optional[int]:
        """Try to extract the printed (logical) page number from a PDF page footer.

        Clips the bottom 5% of the page and looks for the last line that is
        purely 1-4 digits — that is reliably the printed page number in most
        typeset PDFs.  Returns None if nothing suitable is found.
        """
        import re

        rect = page.rect
        footer_rect = type(rect)(0, rect.height * 0.95, rect.width, rect.height)
        text = page.get_text("text", clip=footer_rect).strip()
        if not text:
            return None
        for line in reversed(text.splitlines()):
            line = line.strip()
            if re.fullmatch(r"\d{1,4}", line):
                return int(line)
        return None

    def _extract_pdf(self, content: bytes):
        """Two-pass extraction returning (text, heading_map, page_map).

        Pass 1 – collect font-size distribution to determine body size and
                 build a size→level map for headings.
        Pass 2 – extract text blocks, record heading positions, and track
                 page boundaries so that each chunk can carry a page_number.

        page_map: list of [char_offset, page_number] pairs (1-indexed pages),
        one entry per page marking where that page's content starts in the
        extracted text.  Use _get_page_for_char() to look up any offset.
        """
        from collections import Counter

        import fitz

        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as exc:
            raise ValueError(f"Cannot open PDF: {exc}") from exc

        # ── Pass 1: font-size distribution ───────────────────────────────
        size_chars: Counter = Counter()
        for page in doc:
            for block in page.get_text("dict")["blocks"]:
                if block["type"] == 0:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            t = span["text"].strip()
                            if t:
                                size_chars[round(span["size"], 1)] += len(t)

        if not size_chars:
            doc.close()
            raise ValueError(
                "No text could be extracted from this PDF. "
                "It may be a scanned document — OCR is not supported yet."
            )

        body_size = size_chars.most_common(1)[0][0]
        # Sizes meaningfully larger than body text (≥5% bigger) are headings
        heading_sizes = sorted([s for s in size_chars if s > body_size * 1.05], reverse=True)
        size_to_level = {s: min(i + 1, 6) for i, s in enumerate(heading_sizes)}

        # ── Pass 2: structured text extraction ───────────────────────────
        text_parts: List[str] = []
        headings: List[Dict[str, Any]] = []
        # page_map entries: [char_offset, physical_page, logical_page_or_null]
        # logical_page is the printed number extracted from the footer (may be None)
        page_map: List[List] = []
        current_pos = 0

        for page in doc:
            page_num = page.number + 1  # 1-indexed physical
            logical_num = self._extract_footer_page_number(page)
            page_start_pos = current_pos
            has_content = False

            for block in page.get_text("dict")["blocks"]:
                if block["type"] != 0:
                    continue

                block_lines: List[str] = []
                block_size_chars: Counter = Counter()

                for line in block["lines"]:
                    line_text = "".join(s["text"] for s in line["spans"]).strip()
                    if line_text:
                        block_lines.append(line_text)
                        for span in line["spans"]:
                            if span["text"].strip():
                                block_size_chars[round(span["size"], 1)] += len(
                                    span["text"].strip()
                                )

                if not block_lines:
                    continue

                block_text = "\n".join(block_lines)

                # Heading detection: dominant font size + reasonable length
                if block_size_chars:
                    dom_size = block_size_chars.most_common(1)[0][0]
                    level = size_to_level.get(dom_size)
                    if level is not None and len(block_text) < 200:
                        headings.append(
                            {
                                "pos": current_pos,
                                "level": level,
                                # Display text: collapse internal newlines to space
                                "text": block_text.replace("\n", " "),
                            }
                        )

                text_parts.append(block_text)
                current_pos += len(block_text) + 2  # +2 for "\n\n" separator
                has_content = True

            # Record page boundary only if page had extractable text
            if has_content:
                page_map.append([page_start_pos, page_num, logical_num])

        doc.close()

        full_text = sanitize_text_content("\n\n".join(text_parts))

        # Sanity-check: very little text likely means a scanned PDF
        if len(full_text.strip()) < 100:
            raise ValueError(
                "Extracted text is too short (< 100 chars). "
                "This PDF may be a scanned document — OCR is not supported yet."
            )

        return full_text, headings, page_map

    def extract_text(self, content: Union[str, bytes], metadata: Dict[str, Any]) -> str:
        logger.debug("Extracting text from .pdf file")
        text, _, _ = self._extract_pdf(self._to_bytes(content))
        return text

    def extract_heading_map(self, content: Union[str, bytes]) -> List[Dict[str, Any]]:
        """Extract heading positions from a PDF for structural metadata indexing."""
        _, headings, _ = self._extract_pdf(self._to_bytes(content))
        return headings

    def extract_page_map(self, content: Union[str, bytes]) -> List[List[int]]:
        """Extract page boundary map: [[char_offset, page_number], ...] (1-indexed).

        Each entry marks the character offset in the extracted text where a new
        page begins.  Use _get_page_for_char() in document_processor to look up
        the page number for any chunk by its start_char.
        """
        _, _, page_map = self._extract_pdf(self._to_bytes(content))
        return page_map

    def extract_metadata(self, content: Union[str, bytes], filename: str) -> Dict[str, Any]:
        import fitz

        try:
            doc = fitz.open(stream=self._to_bytes(content), filetype="pdf")
        except Exception:
            return {"file_type": "pdf", "filename": filename}

        meta = doc.metadata or {}
        page_count = doc.page_count
        doc.close()

        return {
            "file_type": "pdf",
            "filename": filename,
            "page_count": page_count,
            "title": meta.get("title") or None,
            "author": meta.get("author") or None,
            "creator": meta.get("creator") or None,
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
        PDFFileHandler(),
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
