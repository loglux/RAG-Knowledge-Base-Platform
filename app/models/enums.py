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

    SIMPLE = "simple"  # Fixed-size chunking (basic, fast)
    SMART = "smart"  # Recursive/paragraph-aware chunking (LangChain)
    SEMANTIC = "semantic"  # Semantic chunking with embeddings (future)


class FileType(str, Enum):
    """Supported file types."""

    TXT = "txt"
    MD = "md"
    FB2 = "fb2"
    DOCX = "docx"
    PDF = "pdf"
    # Future formats (Phase 2+)
    # HTML = "html"
    # CSV = "csv"
    # JSON = "json"


class RetrievalMode(str, Enum):
    """Retrieval mode for RAG."""

    DENSE = "dense"
    HYBRID = "hybrid"
