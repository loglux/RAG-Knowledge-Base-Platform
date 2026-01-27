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

    # OpenAI
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key (required)")
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-large",
        description="OpenAI embedding model"
    )
    OPENAI_CHAT_MODEL: str = Field(
        default="gpt-4-turbo-preview",
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
        default=120,
        description="Timeout in seconds for Ollama chat requests"
    )

    # LLM Provider Selection
    LLM_PROVIDER: str = Field(
        default="openai",
        description="LLM provider for chat (openai, anthropic, ollama)"
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
        default="txt,md",
        description="Comma-separated list of allowed file extensions (MVP: txt,md)"
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
    STRUCTURE_ANALYSIS_LLM_TEMPERATURE: float = Field(
        default=0.3,
        description="LLM temperature for structure analysis (lower = more consistent JSON)"
    )
    STRUCTURE_ANALYSIS_QDRANT_PAGE_SIZE: int = Field(
        default=100,
        description="Qdrant scroll page size when fetching document chunks"
    )

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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiration in minutes")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")

    # CORS
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8004",
        description="Comma-separated list of allowed CORS origins"
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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience: import settings directly
settings = get_settings()
