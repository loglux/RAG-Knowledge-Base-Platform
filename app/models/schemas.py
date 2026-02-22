"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ChunkingStrategy, DocumentStatus, FileType, RetrievalMode

# ============================================================================
# Knowledge Base Schemas
# ============================================================================


class KnowledgeBaseBase(BaseModel):
    """Base schema for Knowledge Base."""

    name: str = Field(..., min_length=1, max_length=255, description="Knowledge base name")
    description: Optional[str] = Field(None, description="Knowledge base description")

    # Embedding configuration
    embedding_model: str = Field(
        default="text-embedding-3-large",
        description="Embedding model name (e.g., text-embedding-3-large, voyage-4)",
    )

    # Chunking configuration
    chunk_size: int = Field(default=1000, ge=100, le=4000, description="Chunk size in characters")
    chunk_overlap: int = Field(
        default=200, ge=0, le=1000, description="Chunk overlap in characters"
    )
    chunking_strategy: ChunkingStrategy = Field(
        default=ChunkingStrategy.FIXED_SIZE, description="Chunking strategy"
    )
    upsert_batch_size: int = Field(
        default=256, ge=64, le=1024, description="Max vectors per upsert request"
    )

    # BM25 configuration (optional overrides)
    bm25_match_mode: Optional[str] = Field(
        default=None, description="BM25 match mode: strict, balanced, loose"
    )
    bm25_min_should_match: Optional[int] = Field(
        default=None, ge=0, le=100, description="BM25 minimum_should_match percentage (0-100)"
    )
    bm25_use_phrase: Optional[bool] = Field(
        default=None, description="Include match_phrase clause in BM25 query"
    )
    bm25_analyzer: Optional[str] = Field(
        default=None, description="BM25 analyzer profile: auto, mixed, ru, en"
    )
    structure_llm_model: Optional[str] = Field(
        default=None, description="LLM model for document structure (TOC) analysis"
    )
    use_llm_chat_titles: Optional[bool] = Field(
        default=None, description="Override for LLM-generated chat titles (None = use app default)"
    )

    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap(cls, v: int, info) -> int:
        """Ensure overlap is less than chunk size."""
        chunk_size = info.data.get("chunk_size", 1000)
        if v >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        return v


class KnowledgeBaseCreate(KnowledgeBaseBase):
    """Schema for creating a new Knowledge Base."""

    chunk_size: Optional[int] = Field(None, ge=100, le=4000)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=1000)
    chunking_strategy: Optional[ChunkingStrategy] = Field(
        default=ChunkingStrategy.SMART,
        description="Chunking strategy: simple (fixed-size), smart (recursive), semantic (future)",
    )
    upsert_batch_size: Optional[int] = Field(None, ge=64, le=1024)
    bm25_match_mode: Optional[str] = None
    bm25_min_should_match: Optional[int] = Field(None, ge=0, le=100)
    bm25_use_phrase: Optional[bool] = None
    bm25_analyzer: Optional[str] = None
    structure_llm_model: Optional[str] = None
    use_llm_chat_titles: Optional[bool] = None


class KnowledgeBaseUpdate(BaseModel):
    """Schema for updating a Knowledge Base."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    chunk_size: Optional[int] = Field(None, ge=100, le=4000)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=1000)
    chunking_strategy: Optional[ChunkingStrategy] = None
    upsert_batch_size: Optional[int] = Field(None, ge=64, le=1024)
    bm25_match_mode: Optional[str] = None
    bm25_min_should_match: Optional[int] = Field(None, ge=0, le=100)
    bm25_use_phrase: Optional[bool] = None
    bm25_analyzer: Optional[str] = None
    structure_llm_model: Optional[str] = None
    use_llm_chat_titles: Optional[bool] = None


class KnowledgeBaseResponse(KnowledgeBaseBase):
    """Schema for Knowledge Base response."""

    id: UUID
    collection_name: str
    embedding_provider: str
    embedding_dimension: int
    document_count: int
    total_chunks: int
    user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    model_config = {"from_attributes": True}


class KnowledgeBaseList(BaseModel):
    """Schema for paginated Knowledge Base list."""

    items: List[KnowledgeBaseResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================================
# Document Schemas
# ============================================================================


class DocumentBase(BaseModel):
    """Base schema for Document."""

    filename: str = Field(..., min_length=1, max_length=255, description="Document filename")


class DocumentCreate(DocumentBase):
    """Schema for creating a new Document."""

    knowledge_base_id: UUID = Field(..., description="Knowledge base ID")
    content: str = Field(..., min_length=1, description="Document content")
    file_type: Optional[FileType] = Field(
        None, description="File type (auto-detected if not provided)"
    )

    @field_validator("file_type", mode="before")
    @classmethod
    def detect_file_type(cls, v: Optional[FileType], info) -> FileType:
        """Auto-detect file type from filename if not provided."""
        if v is not None:
            return v

        filename = info.data.get("filename", "")
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if extension == "txt":
            return FileType.TXT
        elif extension == "md":
            return FileType.MD
        elif extension == "fb2":
            return FileType.FB2
        elif extension == "docx":
            return FileType.DOCX
        else:
            raise ValueError(f"Unsupported file type: .{extension}. Supported: txt, md, fb2, docx")


class DocumentUpload(BaseModel):
    """Schema for document file upload."""

    knowledge_base_id: UUID = Field(..., description="Knowledge base ID")
    # File will be handled by FastAPI's UploadFile


class DocumentResponse(DocumentBase):
    """Schema for Document response."""

    id: UUID
    knowledge_base_id: UUID
    file_type: FileType
    file_size: int
    content_hash: str
    status: DocumentStatus
    embeddings_status: DocumentStatus
    bm25_status: DocumentStatus
    error_message: Optional[str] = None
    processing_stage: Optional[str] = None
    progress_percentage: int = 0
    chunk_count: int
    user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    is_deleted: bool
    duplicate_chunks: Optional[dict] = None

    model_config = {"from_attributes": True}


class DocumentList(BaseModel):
    """Schema for paginated Document list."""

    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class DocumentWithContent(DocumentResponse):
    """Schema for Document response with full content."""

    content: str


# ============================================================================
# Search Schemas
# ============================================================================


class SearchRequest(BaseModel):
    """Schema for semantic search request."""

    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    knowledge_base_id: UUID = Field(..., description="Knowledge base ID")
    limit: int = Field(default=10, ge=1, le=50, description="Number of results")


class SearchResult(BaseModel):
    """Schema for search result."""

    document_id: UUID
    filename: str
    content: str
    score: float
    metadata: dict


class SearchResponse(BaseModel):
    """Schema for search response."""

    results: List[SearchResult]
    query: str
    total: int


# ============================================================================
# Health Check Schema
# ============================================================================


class HealthCheck(BaseModel):
    """Schema for health check response."""

    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReadinessCheck(BaseModel):
    """Schema for readiness check response."""

    ready: bool
    checks: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Chat / RAG Schemas
# ============================================================================


class SourceChunk(BaseModel):
    """Schema for a source chunk in chat response."""

    text: str = Field(..., description="Text content")
    score: float = Field(..., description="Relevance score")
    document_id: str = Field(..., description="Source document ID")
    filename: str = Field(..., description="Source filename")
    chunk_index: int = Field(..., description="Chunk index in document")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional retrieval metadata (source type, scores, etc.)"
    )


# ============================================================================
# Retrieval Settings Schemas
# ============================================================================


class RetrievalSettingsUpdate(BaseModel):
    """Schema for retrieval settings overrides."""

    top_k: Optional[int] = Field(default=None, ge=1, le=100)
    retrieval_mode: Optional[RetrievalMode] = Field(default=None)
    lexical_top_k: Optional[int] = Field(default=None, ge=1, le=200)
    hybrid_dense_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    hybrid_lexical_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_context_chars: Optional[int] = Field(default=None, ge=0)
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    use_structure: Optional[bool] = Field(default=None)
    use_mmr: Optional[bool] = Field(default=None)
    mmr_diversity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    context_expansion: Optional[List[str]] = Field(default=None)
    context_window: Optional[int] = Field(default=None, ge=0, le=5)
    rerank_enabled: Optional[bool] = Field(default=None)
    rerank_provider: Optional[str] = Field(default=None)
    rerank_model: Optional[str] = Field(default=None)
    rerank_candidate_pool: Optional[int] = Field(default=None, ge=1, le=100)
    rerank_top_n: Optional[int] = Field(default=None, ge=1, le=100)
    rerank_min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    bm25_match_mode: Optional[str] = Field(default=None)
    bm25_min_should_match: Optional[int] = Field(default=None, ge=0, le=100)
    bm25_use_phrase: Optional[bool] = Field(default=None)
    bm25_analyzer: Optional[str] = Field(default=None)


class EffectiveRetrievalSettings(BaseModel):
    """Schema for resolved retrieval settings."""

    top_k: int = Field(..., ge=1, le=100)
    retrieval_mode: RetrievalMode = Field(...)
    lexical_top_k: int = Field(..., ge=1, le=200)
    hybrid_dense_weight: float = Field(..., ge=0.0, le=1.0)
    hybrid_lexical_weight: float = Field(..., ge=0.0, le=1.0)
    max_context_chars: int = Field(..., ge=0)
    score_threshold: float = Field(..., ge=0.0, le=1.0)
    use_structure: bool = Field(...)
    use_mmr: bool = Field(...)
    mmr_diversity: float = Field(..., ge=0.0, le=1.0)
    context_expansion: Optional[List[str]] = Field(default=None)
    context_window: Optional[int] = Field(default=None, ge=0, le=5)
    rerank_enabled: bool = Field(...)
    rerank_provider: Optional[str] = Field(default=None)
    rerank_model: Optional[str] = Field(default=None)
    rerank_candidate_pool: int = Field(..., ge=1, le=100)
    rerank_top_n: Optional[int] = Field(default=None, ge=1, le=100)
    rerank_min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    bm25_match_mode: Optional[str] = Field(default=None)
    bm25_min_should_match: Optional[int] = Field(default=None, ge=0, le=100)
    bm25_use_phrase: Optional[bool] = Field(default=None)
    bm25_analyzer: Optional[str] = Field(default=None)


class RetrievalSettingsEnvelope(BaseModel):
    """Stored and effective retrieval settings."""

    stored: Optional[RetrievalSettingsUpdate] = Field(default=None)
    effective: EffectiveRetrievalSettings
    explain: Optional[Dict[str, str]] = Field(
        default=None, description="Per-field source for effective retrieval settings"
    )


class RetrieveRequest(RetrievalSettingsUpdate):
    """Schema for retrieve-only request."""

    query: str = Field(..., min_length=1, max_length=2000, description="Search query")
    knowledge_base_id: UUID = Field(..., description="Knowledge base ID")
    document_ids: Optional[List[UUID]] = Field(
        default=None, description="Optional document ID allow-list for retrieval"
    )
    debug: Optional[bool] = Field(
        default=False, description="Include debug info in response (timings, filters, mode)"
    )


class RetrieveResponse(BaseModel):
    """Schema for retrieve-only response."""

    query: str = Field(..., description="Original query")
    knowledge_base_id: UUID = Field(..., description="Knowledge base queried")
    total_found: int = Field(..., description="Number of chunks returned")
    chunks: List[SourceChunk] = Field(..., description="Retrieved chunks")
    context: str = Field(..., description="Assembled context")
    settings: EffectiveRetrievalSettings = Field(..., description="Resolved retrieval settings")
    debug: Optional[Dict[str, Any]] = Field(default=None, description="Debug metadata (optional)")


class ConversationMessage(BaseModel):
    """Single message in conversation history."""

    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")


class ChatMessageResponse(BaseModel):
    """Chat message response (stored conversation history)."""

    id: UUID
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")
    sources: Optional[List[SourceChunk]] = Field(
        default=None, description="Source chunks for assistant messages"
    )
    model: Optional[str] = Field(default=None, description="LLM model used for assistant messages")
    use_self_check: Optional[bool] = Field(
        default=None, description="Whether self-check was applied"
    )
    prompt_version_id: Optional[UUID] = Field(default=None, description="Prompt version used")
    timestamp: datetime
    message_index: int


class ConversationSummary(BaseModel):
    """Conversation list item."""

    id: UUID
    knowledge_base_id: UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConversationSettings(BaseModel):
    """Chat settings stored per conversation."""

    top_k: Optional[int] = Field(default=None, ge=1, le=100)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_context_chars: Optional[int] = Field(default=None, ge=0)
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    llm_model: Optional[str] = None
    llm_provider: Optional[str] = None
    use_structure: Optional[bool] = None
    retrieval_mode: Optional[RetrievalMode] = Field(default=None)
    lexical_top_k: Optional[int] = Field(default=None, ge=1, le=200)
    hybrid_dense_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    hybrid_lexical_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    bm25_match_mode: Optional[str] = Field(default=None)
    bm25_min_should_match: Optional[int] = Field(default=None, ge=0, le=100)
    bm25_use_phrase: Optional[bool] = Field(default=None)
    bm25_analyzer: Optional[str] = Field(default=None)
    use_mmr: Optional[bool] = Field(default=None)
    mmr_diversity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    rerank_enabled: Optional[bool] = Field(default=None)
    rerank_provider: Optional[str] = Field(default=None)
    rerank_model: Optional[str] = Field(default=None)
    rerank_candidate_pool: Optional[int] = Field(default=None, ge=1, le=100)
    rerank_top_n: Optional[int] = Field(default=None, ge=1, le=100)
    rerank_min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    use_self_check: Optional[bool] = Field(default=None)
    use_conversation_history: Optional[bool] = Field(default=None)
    conversation_history_limit: Optional[int] = Field(default=None, ge=0, le=100)
    use_document_filter: Optional[bool] = Field(default=None)
    document_ids: Optional[List[UUID]] = Field(default=None)
    context_expansion: Optional[List[str]] = Field(default=None)
    context_window: Optional[int] = Field(default=None, ge=0, le=5)


class ConversationTitleUpdate(BaseModel):
    """Conversation title update payload."""

    title: Optional[str] = Field(default=None, max_length=255)


class RegenerateChatTitlesRequest(BaseModel):
    """Request to regenerate chat titles for a KB."""

    include_existing: bool = Field(
        default=False, description="Regenerate titles even if they already exist"
    )
    limit: Optional[int] = Field(
        default=None, ge=1, description="Max number of conversations to process"
    )


class RegenerateChatTitlesResponse(BaseModel):
    """Response for chat title regeneration."""

    updated: int
    skipped: int
    total: int


class AppSettingsBase(BaseModel):
    """Global app defaults for chat settings."""

    llm_model: Optional[str] = Field(default=None)
    llm_provider: Optional[str] = Field(default=None)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    top_k: Optional[int] = Field(default=None, ge=1, le=100)
    max_context_chars: Optional[int] = Field(default=None, ge=0)
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    use_structure: Optional[bool] = Field(default=None)
    rerank_enabled: Optional[bool] = Field(default=None)
    rerank_provider: Optional[str] = Field(default=None)
    rerank_model: Optional[str] = Field(default=None)
    rerank_candidate_pool: Optional[int] = Field(default=None, ge=1, le=100)
    rerank_top_n: Optional[int] = Field(default=None, ge=1, le=100)
    rerank_min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    retrieval_mode: Optional[RetrievalMode] = Field(default=None)
    lexical_top_k: Optional[int] = Field(default=None, ge=1, le=200)
    hybrid_dense_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    hybrid_lexical_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    bm25_match_mode: Optional[str] = Field(default=None)
    bm25_min_should_match: Optional[int] = Field(default=None, ge=0, le=100)
    bm25_use_phrase: Optional[bool] = Field(default=None)
    bm25_analyzer: Optional[str] = Field(default=None)
    structure_requests_per_minute: Optional[int] = Field(default=None, ge=0, le=120)
    kb_chunk_size: Optional[int] = Field(default=None, ge=100, le=2000)
    kb_chunk_overlap: Optional[int] = Field(default=None, ge=0, le=500)
    kb_upsert_batch_size: Optional[int] = Field(default=None, ge=64, le=1024)
    use_llm_chat_titles: Optional[bool] = Field(default=None)
    active_prompt_version_id: Optional[UUID] = Field(default=None)
    active_self_check_prompt_version_id: Optional[UUID] = Field(default=None)
    show_prompt_versions: Optional[bool] = Field(default=None)


class AppSettingsResponse(AppSettingsBase):
    id: int
    created_at: datetime
    updated_at: datetime


class AppSettingsUpdate(AppSettingsBase):
    pass


class ConversationDetail(BaseModel):
    """Conversation detail with settings."""

    id: UUID
    knowledge_base_id: UUID
    title: Optional[str] = None
    settings: Optional[ConversationSettings] = None
    created_at: datetime
    updated_at: datetime


class PromptVersionSummary(BaseModel):
    """Prompt version list item."""

    id: UUID
    name: Optional[str] = None
    created_at: datetime


class PromptVersionDetail(BaseModel):
    """Prompt version detail."""

    id: UUID
    name: Optional[str] = None
    system_content: str
    created_at: datetime


class PromptVersionCreate(BaseModel):
    """Create a new prompt version."""

    name: Optional[str] = Field(default=None, max_length=255)
    system_content: str = Field(..., min_length=1)
    activate: bool = Field(default=False)


class SelfCheckPromptVersionSummary(BaseModel):
    """Self-check prompt version list item."""

    id: UUID
    name: Optional[str] = None
    created_at: datetime


class SelfCheckPromptVersionDetail(BaseModel):
    """Self-check prompt version detail."""

    id: UUID
    name: Optional[str] = None
    system_content: str
    created_at: datetime


class SelfCheckPromptVersionCreate(BaseModel):
    """Create a new self-check prompt version."""

    name: Optional[str] = Field(default=None, max_length=255)
    system_content: str = Field(..., min_length=1)
    activate: bool = Field(default=False)


class ChatRequest(BaseModel):
    """Schema for chat/query request."""

    question: str = Field(..., min_length=1, max_length=2000, description="User's question")
    knowledge_base_id: UUID = Field(..., description="Knowledge base to query")
    conversation_id: Optional[UUID] = Field(
        default=None, description="Conversation ID for persistent chat (optional)"
    )
    conversation_history: Optional[List["ConversationMessage"]] = Field(
        default=None, description="Previous messages in conversation (for follow-up questions)"
    )
    top_k: int = Field(default=5, ge=1, le=100, description="Number of chunks to retrieve")
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="LLM temperature for response generation"
    )
    retrieval_mode: RetrievalMode = Field(
        default=RetrievalMode.DENSE, description="Retrieval mode (dense or hybrid)"
    )
    lexical_top_k: Optional[int] = Field(
        default=None, ge=1, le=200, description="Lexical top K for hybrid (optional)"
    )
    hybrid_dense_weight: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Dense weight for hybrid retrieval"
    )
    hybrid_lexical_weight: float = Field(
        default=0.4, ge=0.0, le=1.0, description="Lexical weight for hybrid retrieval"
    )
    bm25_match_mode: Optional[str] = Field(
        default=None, description="BM25 match mode: strict, balanced, loose"
    )
    bm25_min_should_match: Optional[int] = Field(
        default=None, ge=0, le=100, description="BM25 minimum_should_match percentage (0-100)"
    )
    bm25_use_phrase: Optional[bool] = Field(
        default=None, description="Include match_phrase clause in BM25 query"
    )
    bm25_analyzer: Optional[str] = Field(
        default=None, description="BM25 analyzer profile: auto, mixed, ru, en"
    )
    max_context_chars: Optional[int] = Field(
        default=None, ge=0, description="Max context length in characters (0 = unlimited)"
    )
    score_threshold: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Minimum similarity score for retrieved chunks"
    )
    max_tokens: Optional[int] = Field(
        default=None, ge=1, description="Max tokens for the generated response"
    )
    llm_model: Optional[str] = Field(
        default=None, description="LLM model to use (e.g., gpt-4o, claude-3-5-sonnet-20241022)"
    )
    llm_provider: Optional[str] = Field(
        default=None, description="LLM provider (openai, anthropic, ollama)"
    )
    use_structure: bool = Field(
        default=False, description="Use document structure for search (experimental, default: OFF)"
    )
    rerank_enabled: Optional[bool] = Field(default=None, description="Enable retrieval reranking")
    rerank_provider: Optional[str] = Field(
        default=None, description="Reranking provider (e.g., openai, voyage)"
    )
    rerank_model: Optional[str] = Field(default=None, description="Reranking model name")
    rerank_candidate_pool: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="Candidate pool size before reranking",
    )
    rerank_top_n: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="Number of chunks to keep after reranking (default: top_k)",
    )
    rerank_min_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional minimum rerank score threshold",
    )
    use_mmr: Optional[bool] = Field(
        default=False,
        description="Enable MMR (Maximal Marginal Relevance) for diversity-aware search",
    )
    mmr_diversity: Optional[float] = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="MMR diversity parameter (0.0=pure relevance, 1.0=pure diversity)",
    )
    use_self_check: Optional[bool] = Field(
        default=False, description="Enable self-check validation of generated answers"
    )
    use_conversation_history: Optional[bool] = Field(
        default=None, description="Whether to include conversation history in the prompt"
    )
    conversation_history_limit: Optional[int] = Field(
        default=None, ge=0, le=100, description="Number of recent messages to include from history"
    )
    use_document_filter: Optional[bool] = Field(
        default=None, description="Whether to limit retrieval to selected documents"
    )
    document_ids: Optional[List[UUID]] = Field(
        default=None, description="Optional document ID allow-list for retrieval"
    )
    context_expansion: Optional[List[str]] = Field(
        default=None, description="Context expansion strategies (e.g., ['window'])"
    )
    context_window: Optional[int] = Field(
        default=None,
        ge=0,
        le=5,
        description="Window size (chunks on each side) for windowed retrieval",
    )


class ChatResponse(BaseModel):
    """Schema for chat/query response."""

    answer: str = Field(..., description="Generated answer")
    sources: List[SourceChunk] = Field(..., description="Source chunks used")
    query: str = Field(..., description="Original question")
    confidence_score: float = Field(..., description="Average relevance score")
    model: str = Field(..., description="Model used for generation")
    knowledge_base_id: UUID = Field(..., description="Knowledge base queried")
    conversation_id: Optional[UUID] = Field(
        default=None, description="Conversation ID for persistent chat"
    )
    user_message_id: Optional[UUID] = Field(default=None, description="Stored user message ID")
    assistant_message_id: Optional[UUID] = Field(
        default=None, description="Stored assistant message ID"
    )
    prompt_version_id: Optional[UUID] = Field(default=None, description="Prompt version used")
    use_mmr: Optional[bool] = Field(default=None, description="Whether MMR was used")
    mmr_diversity: Optional[float] = Field(
        default=None, description="MMR diversity parameter (0.0-1.0)"
    )
    use_self_check: Optional[bool] = Field(
        default=None, description="Whether self-check was applied"
    )


class ChatDeleteResponse(BaseModel):
    """Schema for chat message deletion response."""

    status: str = Field(..., description="Deletion status")
    deleted_ids: List[UUID] = Field(default_factory=list, description="Deleted message IDs")


# ============================================================================
# Document Structure Schemas
# ============================================================================


class TOCSection(BaseModel):
    """Section in table of contents."""

    id: str = Field(..., description="Unique section ID")
    title: str = Field(..., description="Section title")
    type: str = Field(..., description="Section type (question, section, chapter, etc.)")
    chunk_start: int = Field(..., description="Starting chunk index")
    chunk_end: int = Field(..., description="Ending chunk index")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    subsections: List["TOCSection"] = Field(default_factory=list, description="Nested subsections")


class DocumentStructureAnalysis(BaseModel):
    """Result of document structure analysis."""

    document_type: str = Field(..., description="Detected document type")
    description: str = Field(..., description="Brief description of structure")
    sections: List[TOCSection] = Field(..., description="Table of contents sections")
    total_sections: int = Field(..., description="Total number of sections")


class DocumentStructureResponse(BaseModel):
    """Schema for document structure response."""

    id: UUID
    document_id: UUID
    document_type: Optional[str]
    sections: List[TOCSection]
    approved_by_user: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# Auth Schemas
# ============================================================================


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    admin_id: int
    username: str
    role: str


class MeResponse(BaseModel):
    admin_id: int
    username: str
    role: str


# ============================================================================
# KB Export/Import Schemas
# ============================================================================


class KBExportInclude(BaseModel):
    """Toggle export/import components for KB transfer."""

    documents: bool = True
    vectors: bool = True
    bm25: bool = True
    uploads: bool = True
    chats: bool = False


class KBExportRequest(BaseModel):
    """Request body for KB export."""

    kb_ids: List[UUID]
    include: Optional[KBExportInclude] = None


class KBImportOptions(BaseModel):
    """Options for KB import."""

    mode: str = Field(default="create", description="create|merge|replace")
    remap_ids: bool = Field(default=True, description="Generate new KB/document IDs on import")
    target_kb_id: Optional[UUID] = Field(
        default=None,
        description="Target KB ID for merge; only valid when mode=merge and archive has a single KB",
    )
    include: Optional[KBExportInclude] = None


class KBImportResponse(BaseModel):
    """Response for KB import."""

    status: str
    kb_imported: int
    kb_created: int
    kb_updated: int
    warnings: List[str] = Field(default_factory=list)


# ============================================================================
# QA Auto-Tuning Schemas
# ============================================================================


class QASampleResponse(BaseModel):
    id: UUID
    knowledge_base_id: UUID
    question: str
    answer: str
    document_id: Optional[UUID] = None
    chunk_index: Optional[int] = None
    source_span: Optional[str] = None
    sample_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class QASampleUploadResponse(BaseModel):
    knowledge_base_id: UUID
    added_count: int
    replaced: bool


class QAEvalRunRequest(BaseModel):
    top_k: int = Field(default=5, ge=1, le=50)
    retrieval_mode: RetrievalMode = Field(default=RetrievalMode.DENSE)
    lexical_top_k: Optional[int] = Field(default=None, ge=1, le=50)
    hybrid_dense_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    hybrid_lexical_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    bm25_match_mode: Optional[str] = None
    bm25_min_should_match: Optional[int] = Field(default=None, ge=0, le=100)
    bm25_use_phrase: Optional[bool] = None
    bm25_analyzer: Optional[str] = None
    max_context_chars: Optional[int] = Field(default=None, ge=1000, le=50000)
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    llm_model: Optional[str] = None
    llm_provider: Optional[str] = None
    use_mmr: bool = False
    mmr_diversity: float = Field(default=0.5, ge=0.0, le=1.0)
    sample_limit: Optional[int] = Field(default=None, ge=1, le=1000)


class QAEvalRunResponse(BaseModel):
    id: UUID
    knowledge_base_id: UUID
    mode: str
    status: str
    config: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    sample_count: int
    processed_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class QAEvalResultResponse(BaseModel):
    id: UUID
    sample_id: Optional[UUID] = None
    question: str
    expected_answer: str
    answer: Optional[str] = None
    document_id: Optional[UUID] = None
    chunk_index: Optional[int] = None
    source_span: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    created_at: datetime


class QAEvalRunDetailResponse(BaseModel):
    run: QAEvalRunResponse
    results: List[QAEvalResultResponse]
