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
    SEMANTIC = "semantic"  # Embedding-based semantic boundary detection


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


class CrawlScope(str, Enum):
    """How far a URL crawl is allowed to wander from the seed URL."""

    DOMAIN = "domain"  # same registered host as the seed URL
    PATH_PREFIX = "path_prefix"  # same host AND same path prefix as the seed URL
    UNRESTRICTED = "unrestricted"  # follow links to any host (still capped by max_pages)


class CrawlJobStatus(str, Enum):
    """Status of a multi-page URL crawl job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
