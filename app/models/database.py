"""SQLAlchemy database models."""
import json
import uuid
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
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
        SQLEnum(ChunkingStrategy, values_callable=lambda x: [e.value for e in x]),
        default=ChunkingStrategy.SMART,
        nullable=False
    )
    upsert_batch_size: Mapped[int] = mapped_column(
        Integer,
        default=256,
        nullable=False,
        comment="Max number of vectors to upsert per request"
    )

    # BM25 (lexical) retrieval configuration (optional overrides)
    bm25_match_mode: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="BM25 match mode: strict, balanced, loose"
    )
    bm25_min_should_match: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="BM25 minimum_should_match percentage (0-100)"
    )
    bm25_use_phrase: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="Include match_phrase clause in BM25 query"
    )
    bm25_analyzer: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="BM25 analyzer profile: auto, mixed, ru, en"
    )
    structure_llm_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="LLM model for document structure (TOC) analysis"
    )
    use_llm_chat_titles: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="Override for LLM-generated chat titles (True/False), None = use app default"
    )
    retrieval_settings_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-encoded retrieval settings overrides"
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
    file_type: Mapped[FileType] = mapped_column(
        SQLEnum(FileType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
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
        SQLEnum(DocumentStatus, values_callable=lambda x: [e.value for e in x]),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True
    )
    embeddings_status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus, values_callable=lambda x: [e.value for e in x]),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True,
        comment="Embedding/Qdrant indexing status"
    )
    bm25_status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus, values_callable=lambda x: [e.value for e in x]),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True,
        comment="BM25/OpenSearch indexing status"
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Processing progress tracking
    processing_stage: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Current processing stage (e.g., 'Chunking', 'Embedding 50/100')"
    )
    progress_percentage: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Processing progress 0-100%"
    )

    # Chunking results
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Vector IDs in Qdrant (stored as JSON-like text)
    vector_ids: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated list of Qdrant vector IDs"
    )

    # Duplicate chunk analysis (JSON string)
    duplicate_chunks_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON with duplicate chunk analysis summary"
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

    @property
    def duplicate_chunks(self):
        if not self.duplicate_chunks_json:
            return None
        try:
            return json.loads(self.duplicate_chunks_json)
        except Exception:
            return None


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


class Conversation(Base):
    """Conversation model - represents a chat thread for a knowledge base."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    settings_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-encoded chat settings overrides"
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Owner user ID - nullable for MVP"
    )

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

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, kb_id={self.knowledge_base_id})>"


class PromptVersion(Base):
    """Prompt version model - stores editable system prompts."""

    __tablename__ = "prompt_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    system_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Creator user ID (nullable for MVP)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<PromptVersion(id={self.id}, name={self.name})>"


class SelfCheckPromptVersion(Base):
    """Prompt version model for self-check validation."""

    __tablename__ = "self_check_prompt_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    system_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Creator user ID (nullable for MVP)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<SelfCheckPromptVersion(id={self.id}, name={self.name})>"


class ChatMessage(Base):
    """Chat message model - represents a single message in a conversation."""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-encoded list of source chunks (assistant messages only)"
    )
    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="LLM model used for assistant messages"
    )
    use_self_check: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="Whether self-check was applied for assistant messages"
    )
    prompt_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_versions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Prompt version used to generate this message"
    )
    message_index: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"


class AppSettings(Base):
    """Global application settings."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    llm_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    llm_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    top_k: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_context_chars: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_threshold: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    use_structure: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    retrieval_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    lexical_top_k: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hybrid_dense_weight: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    hybrid_lexical_weight: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    bm25_match_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bm25_min_should_match: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bm25_use_phrase: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    bm25_analyzer: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    structure_requests_per_minute: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kb_chunk_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kb_chunk_overlap: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kb_upsert_batch_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    use_llm_chat_titles: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    active_prompt_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_versions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Active prompt version for RAG system prompt"
    )
    active_self_check_prompt_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("self_check_prompt_versions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Active prompt version for self-check validation"
    )
    show_prompt_versions: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="Whether to display prompt version in chat responses"
    )

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
        return f"<AppSettings(id={self.id})>"


class AdminUser(Base):
    """Admin user model - for system administration access."""

    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt password hash"
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )
    role: Mapped[str] = mapped_column(
        String(50),
        default="admin",
        nullable=False,
        comment="User role: admin, superadmin"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<AdminUser(id={self.id}, username='{self.username}', role={self.role})>"


class AdminRefreshToken(Base):
    """Refresh token records for admin users."""

    __tablename__ = "admin_refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    admin_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    jti: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    admin_user: Mapped["AdminUser"] = relationship("AdminUser")


class MCPToken(Base):
    """Bearer tokens for MCP endpoint access."""

    __tablename__ = "mcp_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    admin_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[Optional[str]] = mapped_column(
        String(120),
        nullable=True,
        comment="Human-friendly label for the token"
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="SHA256 hash of the token"
    )
    token_prefix: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
        comment="Token prefix for display"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    admin_user: Mapped["AdminUser"] = relationship("AdminUser")


class MCPRefreshToken(Base):
    """Refresh tokens for MCP OAuth flow."""

    __tablename__ = "mcp_refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    admin_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    jti: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    admin_user: Mapped["AdminUser"] = relationship("AdminUser")


class SystemSettings(Base):
    """System configuration settings - stores API keys, database URLs, etc."""

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Setting key (e.g., 'openai_api_key', 'qdrant_url')"
    )
    value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Setting value (encrypted if is_encrypted=True)"
    )
    is_encrypted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether value is encrypted (for API keys, passwords)"
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Setting category: api, database, system, limits"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable description of the setting"
    )

    # Audit fields
    updated_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Admin user who last updated this setting"
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
        return f"<SystemSettings(key='{self.key}', category={self.category}, encrypted={self.is_encrypted})>"


class QASample(Base):
    """Evaluation sample for QA-based RAG tuning."""

    __tablename__ = "qa_samples"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )
    chunk_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_span: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    sample_type: Mapped[str] = mapped_column(
        String(20),
        default="gold",
        nullable=False,
        index=True,
        comment="gold | synthetic | self_consistency"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<QASample(id={self.id}, kb_id={self.knowledge_base_id})>"


class QAEvalRun(Base):
    """Run metadata for QA-based evaluation."""

    __tablename__ = "qa_eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    mode: Mapped[str] = mapped_column(
        String(20),
        default="gold",
        nullable=False,
        comment="gold | synthetic | self_consistency"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        comment="pending | running | completed | failed"
    )
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<QAEvalRun(id={self.id}, kb_id={self.knowledge_base_id}, status={self.status})>"


class QAEvalResult(Base):
    """Per-sample results for a QA evaluation run."""

    __tablename__ = "qa_eval_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("qa_eval_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    sample_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("qa_samples.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sources_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<QAEvalResult(id={self.id}, run_id={self.run_id})>"
