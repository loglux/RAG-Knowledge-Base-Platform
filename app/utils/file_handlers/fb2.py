"""FB2 (FictionBook 2.0) file handler."""

from typing import Any, Dict, List, Optional, Union
from xml.etree import ElementTree

from app.models.enums import FileType
from app.utils.file_handlers.base import ExtractResult, FileHandler
from app.utils.logger import get_logger
from app.utils.validators import sanitize_text_content

logger = get_logger(__name__)


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
        except ElementTree.ParseError as exc:
            logger.debug("FB2 strict parse failed, falling back to lxml recovery: %s", exc)
        try:
            from lxml import etree

            root_lxml = etree.fromstring(
                content.encode("utf-8") if isinstance(content, str) else content,
                parser=etree.XMLParser(recover=True, encoding="utf-8"),
            )
            # Convert lxml tree to stdlib ElementTree via serialization
            reparsed = ElementTree.fromstring(etree.tostring(root_lxml))
            return reparsed
        except Exception as exc:
            logger.debug("FB2 lxml recovery parse failed: %s", exc)
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
        return self._metadata_from_tree(root, filename, content)

    @staticmethod
    def _metadata_from_tree(root, filename: str, raw_content: str) -> Dict[str, Any]:
        if root is None:
            return {
                "file_type": "fb2",
                "filename": filename,
                "char_count": len(raw_content),
                "word_count": len(raw_content.split()),
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
            "char_count": len(raw_content),
            "word_count": len(raw_content.split()),
        }

    def extract_all(
        self,
        content: Union[str, bytes],
        filename: str,
        profile_overrides: Optional[Dict[str, Any]] = None,
    ) -> ExtractResult:
        """One-pass FB2 extraction: parse XML once, derive text + headings + metadata.

        ``profile_overrides`` is accepted for signature uniformity but ignored —
        FB2 has no tunable extraction params yet.
        """
        del profile_overrides
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")

        root = self._parse_xml(content)
        metadata = self._metadata_from_tree(root, filename, content)

        if root is None:
            return ExtractResult(text=sanitize_text_content(content), metadata=metadata)

        all_segments: List[Dict[str, Any]] = []
        for node in root.iter():
            if node.tag.endswith("body"):
                all_segments.extend(self._parse_body(node))

        if not all_segments:
            fallback = " ".join(t for t in root.itertext() if t.strip())
            return ExtractResult(
                text=sanitize_text_content(fallback),
                metadata=metadata,
            )

        text = sanitize_text_content("\n\n".join(seg["text"] for seg in all_segments))

        headings: List[Dict[str, Any]] = []
        current_pos = 0
        for seg in all_segments:
            if seg["is_heading"] and 1 <= seg["level"] <= 6:
                headings.append({"pos": current_pos, "level": seg["level"], "text": seg["text"]})
            current_pos += len(seg["text"]) + 2

        return ExtractResult(
            text=text,
            metadata=metadata,
            headings=headings if headings else None,
        )
