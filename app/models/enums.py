"""Enumerations for the application."""
from enum import Enum


class DocumentStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ChunkingStrategy(str, Enum):
    """Text chunking strategy."""

    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    PARAGRAPH = "paragraph"


class FileType(str, Enum):
    """Supported file types."""

    TXT = "txt"
    MD = "md"
    # Future formats (Phase 2+)
    # PDF = "pdf"
    # DOCX = "docx"
    # HTML = "html"
    # CSV = "csv"
    # JSON = "json"


class RetrievalMode(str, Enum):
    """Retrieval mode for RAG."""

    DENSE = "dense"
    HYBRID = "hybrid"
