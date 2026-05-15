"""Base types for file handlers: ExtractResult dataclass and FileHandler ABC."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from app.models.enums import FileType
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractResult:
    """Result of one-shot file extraction.

    Combines text, metadata, and (where applicable) structural maps so the
    document can be parsed exactly once instead of separately per piece.

    Attributes:
        text: Sanitised full text of the document.
        metadata: File-level metadata (filename, page_count, title, …).
        headings: Optional list of {pos, level, text} entries.
        page_map: Optional list of [char_offset, physical_page, logical_page]
                  entries (PDF only).
    """

    text: str
    metadata: Dict[str, Any]
    headings: Optional[List[Dict[str, Any]]] = None
    page_map: Optional[List[List[int]]] = None


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

    def extract_all(self, content: Union[str, bytes], filename: str) -> ExtractResult:
        """Extract text, metadata, and any structural data in a single logical pass.

        Default implementation calls extract_metadata() and extract_text() separately.
        Subclasses with expensive parsing (PDF, DOCX, FB2) override this so that
        the underlying file is parsed exactly once per upload.
        """
        metadata = self.extract_metadata(content, filename)
        text = self.extract_text(content, metadata)
        headings: Optional[List[Dict[str, Any]]] = None
        if hasattr(self, "extract_heading_map"):
            try:
                headings = self.extract_heading_map(content) or None
            except Exception as exc:
                logger.warning("Heading map extraction failed: %s", exc)
        return ExtractResult(text=text, metadata=metadata, headings=headings)
