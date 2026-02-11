"""Application configuration using Pydantic Settings."""
from typing import List, Optional
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=True, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8000, description="API port")
    API_PREFIX: str = Field(default="/api/v1", description="API prefix")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://kb_user:kb_pass@localhost:5434/knowledge_base",
        description="PostgreSQL database URL with asyncpg driver"
    )
    DB_ECHO: bool = Field(default=False, description="Echo SQL queries")
    DB_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Database max overflow connections")

    # Qdrant Vector Database
    QDRANT_URL: str = Field(default="http://localhost:6334", description="Qdrant HTTP API URL")
    QDRANT_GRPC_URL: Optional[str] = Field(default=None, description="Qdrant gRPC URL (optional)")
    QDRANT_API_KEY: Optional[str] = Field(default=None, description="Qdrant API key (optional)")
    QDRANT_COLLECTION_NAME: str = Field(default="knowledge_base_vectors", description="Default collection name")
    QDRANT_VECTOR_SIZE: int = Field(
        default=1536,
        description="Default vector embedding size (fallback, actual size determined by embedding model)"
    )

    # OpenSearch (BM25 lexical search)
    OPENSEARCH_URL: str = Field(default="http://localhost:9200", description="OpenSearch HTTP URL")
    OPENSEARCH_INDEX: str = Field(default="kb_chunks", description="OpenSearch index for lexical chunks")
    OPENSEARCH_USERNAME: Optional[str] = Field(default=None, description="OpenSearch username (optional)")
    OPENSEARCH_PASSWORD: Optional[str] = Field(default=None, description="OpenSearch password (optional)")
    OPENSEARCH_VERIFY_CERTS: bool = Field(default=False, description="Verify OpenSearch TLS certs")
    BM25_MATCH_MODES: List[str] = Field(
        default=["strict", "balanced", "loose"],
        description="Allowed BM25 match modes"
    )
    BM25_ANALYZERS: List[str] = Field(
        default=["auto", "mixed", "ru", "en"],
        description="Allowed BM25 analyzer profiles"
    )
    BM25_DEFAULT_MATCH_MODE: str = Field(
        default="balanced",
        description="Default BM25 match mode"
    )
    BM25_DEFAULT_MIN_SHOULD_MATCH: int = Field(
        default=50,
        description="Default BM25 minimum_should_match percentage"
    )
    BM25_DEFAULT_USE_PHRASE: bool = Field(
        default=True,
        description="Default BM25 phrase match toggle"
    )
    BM25_DEFAULT_ANALYZER: str = Field(
        default="mixed",
        description="Default BM25 analyzer profile"
    )

    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key (configured via Setup Wizard)")
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-large",
        description="OpenAI embedding model"
    )
    OPENAI_CHAT_MODEL: str = Field(
        default="gpt-4o",
        description="OpenAI chat model"
    )
    OPENAI_MAX_TOKENS: int = Field(default=16000, description="Max tokens for OpenAI responses")
    OPENAI_TEMPERATURE: float = Field(default=0.7, description="Temperature for OpenAI responses")

    # Voyage AI (optional)
    VOYAGE_API_KEY: Optional[str] = Field(default=None, description="Voyage AI API key (optional)")
    VOYAGE_EMBEDDING_MODEL: str = Field(
        default="voyage-4",
        description="Voyage AI embedding model"
    )

    # Anthropic (optional)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key (optional)")
    ANTHROPIC_CHAT_MODEL: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Anthropic chat model"
    )
    ANTHROPIC_MAX_TOKENS: int = Field(default=4000, description="Max tokens for Anthropic responses")

    # DeepSeek (optional)
    DEEPSEEK_API_KEY: Optional[str] = Field(default=None, description="DeepSeek API key (optional)")
    DEEPSEEK_BASE_URL: str = Field(
        default="https://api.deepseek.com",
        description="DeepSeek API base URL"
    )
    DEEPSEEK_CHAT_MODEL: str = Field(
        default="deepseek-chat",
        description="DeepSeek chat model"
    )
    DEEPSEEK_MAX_TOKENS: int = Field(default=8192, description="Max tokens for DeepSeek responses")

    # Ollama (optional)
    OLLAMA_BASE_URL: Optional[str] = Field(default=None, description="Ollama API base URL (optional)")
    OLLAMA_EMBEDDING_MODEL: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model"
    )
    OLLAMA_CHAT_MODEL: str = Field(
        default="llama3.1",
        description="Ollama chat model"
    )
    OLLAMA_TIMEOUT_SECONDS: int = Field(
        default=180,
        description="Timeout in seconds for Ollama chat requests"
    )

    # LLM Provider Selection
    LLM_PROVIDER: str = Field(
        default="openai",
        description="LLM provider for chat (openai, anthropic, deepseek, ollama)"
    )

    # Document Processing
    MAX_CHUNK_SIZE: int = Field(default=1000, description="Maximum chunk size in characters")
    CHUNK_OVERLAP: int = Field(default=200, description="Chunk overlap in characters")
    MAX_FILE_SIZE_MB: int = Field(default=50, description="Maximum file size in MB")
    MAX_CONTEXT_CHARS: int = Field(
        default=0,
        description="Maximum assembled context length in characters"
    )
    ALLOWED_FILE_TYPES: str = Field(
        default="txt,md,fb2,docx",
        description="Comma-separated list of allowed file extensions (MVP: txt,md,fb2,docx)"
    )

    # Structure Analysis (LLM-based document TOC generation)
    STRUCTURE_ANALYSIS_MAX_CHUNKS: int = Field(
        default=0,
        description="Max chunks to send for analysis (0 = all chunks, unlimited)"
    )
    STRUCTURE_ANALYSIS_MAX_CHARS_PER_CHUNK: int = Field(
        default=0,
        description="Max chars per chunk for analysis (0 = full chunk, no truncation)"
    )
    STRUCTURE_ANALYSIS_MAX_TOTAL_CHARS: int = Field(
        default=0,
        description="Max total chars for analysis (0 = unlimited, send full document)"
    )
    STRUCTURE_ANALYSIS_LLM_MODEL: str = Field(
        default="claude-haiku-4-5-20251001",
        description="LLM model for structure analysis"
    )
    STRUCTURE_ANALYSIS_REQUESTS_PER_MINUTE: int = Field(
        default=10,
        description="Max structure analysis requests per minute (0 = unlimited)"
    )
    STRUCTURE_ANALYSIS_LLM_TEMPERATURE: float = Field(
        default=0.3,
        description="LLM temperature for structure analysis (lower = more consistent JSON)"
    )
    STRUCTURE_ANALYSIS_QDRANT_PAGE_SIZE: int = Field(
        default=100,
        description="Qdrant scroll page size when fetching document chunks"
    )

    @field_validator("BM25_MATCH_MODES", "BM25_ANALYZERS", mode="before")
    @classmethod
    def _split_csv_list(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    # Query Intent Extraction
    QUERY_INTENT_LLM_TEMPERATURE: float = Field(
        default=0.1,
        description="LLM temperature for query intent extraction (very low = consistent)"
    )

    # Security (prepared for future auth)
    SECRET_KEY: str = Field(
        default="change-this-in-production-use-openssl-rand-hex-32",
        description="Secret key for JWT tokens"
    )

    # MCP (Model Context Protocol)
    MCP_ENABLED: bool = Field(default=False, description="Enable MCP endpoint")
    MCP_PATH: str = Field(default="/mcp", description="MCP endpoint path")
    MCP_PUBLIC_BASE_URL: Optional[str] = Field(
        default=None,
        description="Public base URL for MCP (used for OAuth metadata and endpoint display)"
    )
    MCP_DEFAULT_KB_ID: Optional[str] = Field(default=None, description="Default knowledge base ID for MCP tools")
    MCP_TOOLS_ENABLED: List[str] = Field(
        default=[
            "rag_query",
            "list_knowledge_bases",
            "list_documents",
            "retrieve_chunks",
            "get_kb_retrieval_settings",
            "set_kb_retrieval_settings",
            "clear_kb_retrieval_settings",
        ],
        description="Enabled MCP tool names"
    )

    @field_validator("MCP_TOOLS_ENABLED", mode="before")
    @classmethod
    def _parse_mcp_tools(cls, v):
        if v is None:
            return v
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("["):
                try:
                    import json
                    return json.loads(v)
                except Exception:
                    pass
            return [item.strip() for item in v.split(",") if item.strip()]
        return v
    MCP_OAUTH_ENABLED: bool = Field(
        default=False,
        description="Enable FastMCP OAuth (full /authorize, /token, /.well-known)"
    )
    MCP_OAUTH_PROVIDER: str = Field(
        default="github",
        description="FastMCP OAuth provider (currently supports: github)"
    )
    MCP_OAUTH_CLIENT_ID: Optional[str] = Field(
        default=None,
        description="OAuth client ID for FastMCP provider"
    )
    MCP_OAUTH_CLIENT_SECRET: Optional[str] = Field(
        default=None,
        description="OAuth client secret for FastMCP provider"
    )
    MCP_OAUTH_ISSUER_URL: Optional[str] = Field(
        default=None,
        description="Optional OAuth issuer URL override (for well-known metadata)"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiration in minutes")
    MCP_ACCESS_TOKEN_TTL_MINUTES: Optional[int] = Field(
        default=None,
        description="MCP OAuth access token TTL in minutes (from DB)"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, description="Refresh token expiration in days")
    MCP_REFRESH_TOKEN_TTL_DAYS: Optional[int] = Field(
        default=None,
        description="MCP OAuth refresh token TTL in days (from DB)"
    )
    COOKIE_SECURE: bool = Field(default=False, description="Use secure cookies (HTTPS only)")
    COOKIE_SAMESITE: str = Field(default="lax", description="Cookie SameSite policy (lax/strict/none)")

    # CORS
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5174,http://127.0.0.1:5174,http://localhost:8004",
        description="Comma-separated list of allowed CORS origins"
    )

    # System Settings (can be overridden from database)
    SYSTEM_NAME: str = Field(
        default="Knowledge Base Platform",
        description="System name displayed in UI"
    )

    # Feature Flags
    ENABLE_ASYNC_PROCESSING: bool = Field(default=True, description="Enable async document processing")
    ENABLE_CACHE: bool = Field(default=False, description="Enable caching (Redis required)")
    ENABLE_METRICS: bool = Field(default=False, description="Enable Prometheus metrics")

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        allowed = ["development", "staging", "production"]
        if v.lower() not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v.lower()

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def allowed_file_types_list(self) -> List[str]:
        """Parse allowed file types into list."""
        return [ext.strip().lower() for ext in self.ALLOWED_FILE_TYPES.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size to bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.ENVIRONMENT == "development"

    def update_from_dict(self, updates: dict) -> None:
        """
        Update settings from dictionary.

        Used to override settings from database.

        Args:
            updates: Dictionary of setting_name -> value
        """
        for key, value in updates.items():
            if hasattr(self, key):
                # Convert to appropriate type
                field_type = self.model_fields[key].annotation
                if field_type == int:
                    value = int(value)
                elif field_type == float:
                    value = float(value)
                elif field_type == bool:
                    value = value.lower() in ("true", "1", "yes") if isinstance(value, str) else bool(value)
                elif getattr(field_type, "__origin__", None) is list:
                    if isinstance(value, str):
                        value = value.strip()
                        if value.startswith("["):
                            import json
                            value = json.loads(value)
                        else:
                            value = [item.strip() for item in value.split(",") if item.strip()]

                setattr(self, key, value)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience: import settings directly
settings = get_settings()


async def load_settings_from_db() -> None:
    """
    Load settings from database and override current settings.

    This should be called during application startup.
    """
    try:
        from app.db.session import get_db_session
        from app.core.system_settings import SystemSettingsManager

        async with get_db_session() as db:
            # Load settings from database
            db_settings = await SystemSettingsManager.load_from_db(db)

            if db_settings:
                # Merge with current settings (DB overrides ENV)
                env_settings = {
                    key: getattr(settings, key)
                    for key in dir(settings)
                    if key.isupper() and not key.startswith("_")
                }

                merged = SystemSettingsManager.merge_with_env_settings(
                    db_settings, env_settings
                )

                # Update global settings instance
                settings.update_from_dict(merged)

                import logging
                logger = logging.getLogger(__name__)
                logger.info("Settings loaded from database and applied")

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not load settings from database: {e}")
        logger.info("Using settings from environment variables")


async def is_setup_complete() -> bool:
    """
    Check if initial system setup has been completed.

    Returns:
        True if setup is complete, False if setup wizard should be shown
    """
    try:
        from app.db.session import get_db_session
        from app.core.system_settings import SystemSettingsManager

        async with get_db_session() as db:
            return await SystemSettingsManager.is_setup_complete(db)

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not check setup completion: {e}")
        # If can't check, assume setup needed
        return False
