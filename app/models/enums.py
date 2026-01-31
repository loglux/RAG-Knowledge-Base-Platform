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

    # New naming scheme (preferred)
    SIMPLE = "simple"        # Fixed-size chunking (basic, fast)
    SMART = "smart"          # Recursive/paragraph-aware chunking (LangChain)
    SEMANTIC = "semantic"    # Semantic chunking with embeddings (future)

    # Legacy naming (for backward compatibility with existing DB records)
    FIXED_SIZE = "FIXED_SIZE"  # Old name for SIMPLE
    PARAGRAPH = "PARAGRAPH"    # Old name for SMART


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
