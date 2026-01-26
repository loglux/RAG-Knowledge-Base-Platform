"""SQLAlchemy database models."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, Integer, Boolean, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.models.enums import DocumentStatus, ChunkingStrategy, FileType


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class KnowledgeBase(Base):
    """Knowledge Base model - represents a collection of documents."""

    __tablename__ = "knowledge_bases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Qdrant collection name for this KB
    collection_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # Embedding configuration
    embedding_model: Mapped[str] = mapped_column(
        String(100),
        default="text-embedding-3-large",
        nullable=False,
        comment="Embedding model name (e.g., text-embedding-3-large, voyage-4)"
    )
    embedding_provider: Mapped[str] = mapped_column(
        String(50),
        default="openai",
        nullable=False,
        comment="Embedding provider (openai, voyage)"
    )
    embedding_dimension: Mapped[int] = mapped_column(
        Integer,
        default=3072,
        nullable=False,
        comment="Vector dimension size for embeddings"
    )

    # Chunking configuration
    chunk_size: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    chunking_strategy: Mapped[ChunkingStrategy] = mapped_column(
        SQLEnum(ChunkingStrategy),
        default=ChunkingStrategy.FIXED_SIZE,
        nullable=False
    )
    upsert_batch_size: Mapped[int] = mapped_column(
        Integer,
        default=256,
        nullable=False,
        comment="Max number of vectors to upsert per request"
    )

    # Statistics
    document_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Future: User ownership (nullable for MVP)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Owner user ID - nullable for MVP, will be required later"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="knowledge_base",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBase(id={self.id}, name='{self.name}')>"


class Document(Base):
    """Document model - represents a document in a knowledge base."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    # Knowledge Base relationship
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Document metadata
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[FileType] = mapped_column(SQLEnum(FileType), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, comment="File size in bytes")

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 hash of content for deduplication"
    )

    # Processing status
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Chunking results
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Vector IDs in Qdrant (stored as JSON-like text)
    vector_ids: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated list of Qdrant vector IDs"
    )

    # Future: User ownership (nullable for MVP)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Owner user ID - nullable for MVP"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        "KnowledgeBase",
        back_populates="documents"
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename='{self.filename}', status={self.status})>"


class DocumentStructure(Base):
    """AI-analyzed document structure (table of contents)."""

    __tablename__ = "document_structures"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    # Document relationship
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Table of contents as JSON
    toc_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Hierarchical table of contents in JSON format"
    )

    # Analysis metadata
    document_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Document type detected by LLM (e.g., tma_questions, textbook)"
    )

    # User approval
    approved_by_user: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<DocumentStructure(id={self.id}, document_id={self.document_id})>"
