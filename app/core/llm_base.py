"""
Base classes for LLM providers.

Provides abstract interface for different LLM services (OpenAI, Anthropic, Ollama).
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"


class LLMModel(BaseModel):
    """LLM model configuration."""

    provider: LLMProvider
    model_name: str
    context_window: int
    description: str
    cost_per_million_input_tokens: float
    cost_per_million_output_tokens: float


# Available LLM models
LLM_MODELS = {
    # OpenAI GPT-5 Series (Frontier models 2026)
    "gpt-5.2": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="gpt-5.2",
        context_window=400000,
        description="GPT-5.2 - best for coding and agentic tasks",
        cost_per_million_input_tokens=1.75,
        cost_per_million_output_tokens=14.0,
    ),
    "gpt-5.2-pro": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="gpt-5.2-pro",
        context_window=400000,
        description="GPT-5.2 Pro - smarter and more precise responses",
        cost_per_million_input_tokens=21.0,
        cost_per_million_output_tokens=168.0,
    ),
    "gpt-5.1": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="gpt-5.1",
        context_window=400000,
        description="GPT-5.1 - best for coding with configurable reasoning",
        cost_per_million_input_tokens=1.25,
        cost_per_million_output_tokens=10.0,
    ),
    "gpt-5": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="gpt-5",
        context_window=400000,
        description="GPT-5 - previous intelligent reasoning model",
        cost_per_million_input_tokens=1.25,
        cost_per_million_output_tokens=10.0,
    ),
    "gpt-5-pro": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="gpt-5-pro",
        context_window=400000,
        description="GPT-5 Pro - smarter and more precise responses",
        cost_per_million_input_tokens=15.0,
        cost_per_million_output_tokens=120.0,
    ),
    "gpt-5-mini": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="gpt-5-mini",
        context_window=400000,
        description="GPT-5 mini - faster, cost-efficient for well-defined tasks",
        cost_per_million_input_tokens=0.25,
        cost_per_million_output_tokens=2.0,
    ),
    "gpt-5-nano": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="gpt-5-nano",
        context_window=400000,
        description="GPT-5 nano - fastest, most cost-efficient",
        cost_per_million_input_tokens=0.05,
        cost_per_million_output_tokens=0.40,
    ),
    # OpenAI GPT-4.1 Series
    "gpt-4.1": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="gpt-4.1",
        context_window=1000000,  # 1M context window
        description="GPT-4.1 - smartest non-reasoning model",
        cost_per_million_input_tokens=2.0,
        cost_per_million_output_tokens=8.0,
    ),
    "gpt-4.1-mini": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="gpt-4.1-mini",
        context_window=1000000,
        description="GPT-4.1 mini - smaller, faster version",
        cost_per_million_input_tokens=0.40,
        cost_per_million_output_tokens=1.60,
    ),
    "gpt-4.1-nano": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="gpt-4.1-nano",
        context_window=1000000,
        description="GPT-4.1 nano - fastest, most cost-efficient",
        cost_per_million_input_tokens=0.10,
        cost_per_million_output_tokens=0.40,
    ),
    # OpenAI o-series Reasoning models
    "o3": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="o3",
        context_window=200000,
        description="o3 - reasoning for complex tasks (uses reasoning tokens)",
        cost_per_million_input_tokens=2.0,
        cost_per_million_output_tokens=8.0,
    ),
    "o3-pro": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="o3-pro",
        context_window=200000,
        description="o3-pro - more compute for better responses",
        cost_per_million_input_tokens=4.0,  # estimated
        cost_per_million_output_tokens=16.0,
    ),
    "o3-mini": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="o3-mini",
        context_window=200000,
        description="o3-mini - small alternative to o3",
        cost_per_million_input_tokens=1.0,
        cost_per_million_output_tokens=4.0,
    ),
    "o4-mini": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="o4-mini",
        context_window=200000,
        description="o4-mini - fast, cost-efficient reasoning (superseded by GPT-5 mini)",
        cost_per_million_input_tokens=0.5,
        cost_per_million_output_tokens=2.0,
    ),
    "o1": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="o1",
        context_window=200000,
        description="o1 - previous full o-series reasoning model",
        cost_per_million_input_tokens=15.0,
        cost_per_million_output_tokens=60.0,
    ),
    "o1-pro": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="o1-pro",
        context_window=200000,
        description="o1-pro - version of o1 with more compute",
        cost_per_million_input_tokens=150.0,
        cost_per_million_output_tokens=600.0,
    ),
    "o1-mini": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="o1-mini",
        context_window=200000,
        description="o1-mini - small alternative to o1 (deprecated)",
        cost_per_million_input_tokens=3.0,
        cost_per_million_output_tokens=12.0,
    ),
    # Legacy OpenAI models (keeping for compatibility)
    "gpt-4o": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="gpt-4o",
        context_window=128000,
        description="GPT-4o (legacy) - superseded by GPT-5 series",
        cost_per_million_input_tokens=2.5,
        cost_per_million_output_tokens=10.0,
    ),
    "gpt-4o-mini": LLMModel(
        provider=LLMProvider.OPENAI,
        model_name="gpt-4o-mini",
        context_window=128000,
        description="GPT-4o-mini (legacy) - superseded by GPT-5 mini",
        cost_per_million_input_tokens=0.15,
        cost_per_million_output_tokens=0.60,
    ),
    # Anthropic Claude 4.5 models (latest as of Jan 2026)
    "claude-opus-4-5-20251101": LLMModel(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-opus-4-5-20251101",
        context_window=200000,
        description="Claude Opus 4.5 - premium model with maximum intelligence",
        cost_per_million_input_tokens=5.0,
        cost_per_million_output_tokens=25.0,
    ),
    "claude-sonnet-4-5-20250929": LLMModel(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-sonnet-4-5-20250929",
        context_window=200000,  # 1M beta with context-1m-2025-08-07 header
        description="Claude Sonnet 4.5 - smart model for complex agents and coding",
        cost_per_million_input_tokens=3.0,
        cost_per_million_output_tokens=15.0,
    ),
    "claude-haiku-4-5-20251001": LLMModel(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-haiku-4-5-20251001",
        context_window=200000,
        description="Claude Haiku 4.5 - fastest model with near-frontier intelligence",
        cost_per_million_input_tokens=1.0,
        cost_per_million_output_tokens=5.0,
    ),
    # Legacy Claude 4 models (keeping for compatibility)
    "claude-opus-4-1-20250805": LLMModel(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-opus-4-1-20250805",
        context_window=200000,
        description="Claude Opus 4.1 (legacy)",
        cost_per_million_input_tokens=15.0,
        cost_per_million_output_tokens=75.0,
    ),
    "claude-sonnet-4-20250514": LLMModel(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-sonnet-4-20250514",
        context_window=200000,
        description="Claude Sonnet 4 (legacy)",
        cost_per_million_input_tokens=3.0,
        cost_per_million_output_tokens=15.0,
    ),
    "claude-3-7-sonnet-20250219": LLMModel(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-3-7-sonnet-20250219",
        context_window=200000,
        description="Claude Sonnet 3.7 (legacy)",
        cost_per_million_input_tokens=3.0,
        cost_per_million_output_tokens=15.0,
    ),
    # DeepSeek
    "deepseek-chat": LLMModel(
        provider=LLMProvider.DEEPSEEK,
        model_name="deepseek-chat",
        context_window=128000,
        description="DeepSeek V3.2 (non-thinking mode)",
        cost_per_million_input_tokens=0.28,
        cost_per_million_output_tokens=0.42,
    ),
    "deepseek-reasoner": LLMModel(
        provider=LLMProvider.DEEPSEEK,
        model_name="deepseek-reasoner",
        context_window=128000,
        description="DeepSeek V3.2 (thinking mode)",
        cost_per_million_input_tokens=0.28,
        cost_per_million_output_tokens=0.42,
    ),
    # Ollama models (local, free)
    "llama3.1": LLMModel(
        provider=LLMProvider.OLLAMA,
        model_name="llama3.1",
        context_window=128000,
        description="Meta Llama 3.1 - open source flagship",
        cost_per_million_input_tokens=0.0,  # Free (local)
        cost_per_million_output_tokens=0.0,
    ),
    "qwen2.5": LLMModel(
        provider=LLMProvider.OLLAMA,
        model_name="qwen2.5",
        context_window=32768,
        description="Alibaba Qwen 2.5 - multilingual model",
        cost_per_million_input_tokens=0.0,  # Free (local)
        cost_per_million_output_tokens=0.0,
    ),
    "mistral": LLMModel(
        provider=LLMProvider.OLLAMA,
        model_name="mistral",
        context_window=32768,
        description="Mistral AI - efficient open source model",
        cost_per_million_input_tokens=0.0,  # Free (local)
        cost_per_million_output_tokens=0.0,
    ),
}


class Message(BaseModel):
    """Chat message."""

    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message content")


class LLMResponse(BaseModel):
    """LLM response."""

    content: str = Field(..., description="Generated text")
    model: str = Field(..., description="Model used")
    input_tokens: Optional[int] = Field(None, description="Input tokens used")
    output_tokens: Optional[int] = Field(None, description="Output tokens generated")
    total_tokens: Optional[int] = Field(None, description="Total tokens")
    cache_hit_tokens: Optional[int] = Field(
        None,
        description="Normalized cache-hit input tokens (provider-specific)",
    )
    cache_miss_tokens: Optional[int] = Field(
        None,
        description="Normalized cache-miss input tokens (provider-specific)",
    )
    cache_create_tokens: Optional[int] = Field(
        None,
        description="Tokens used to create cache entries (provider-specific)",
    )


class BaseLLMService(ABC):
    """
    Abstract base class for LLM services.

    All LLM providers must implement this interface.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        max_retries: int = 3,
        skip_validation: bool = False,
    ):
        """
        Initialize LLM service.

        Args:
            api_key: API key for the provider (or "local" for Ollama)
            model: Model name to use
            max_retries: Maximum number of retries for failed requests
            skip_validation: Skip model validation (for dynamic Ollama models)
        """
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries

        # Get model configuration (skip for dynamic models)
        if skip_validation:
            self.model_config = None
            return

        if model not in LLM_MODELS:
            raise ValueError(f"Unknown LLM model: {model}")

        self.model_config = LLM_MODELS[model]

    @property
    def provider(self) -> LLMProvider:
        """Get the provider type."""
        if self.model_config:
            return self.model_config.provider
        return None

    @property
    def context_window(self) -> int:
        """Get the context window size."""
        if self.model_config:
            return self.model_config.context_window
        return None

    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate text completion.

        Args:
            messages: List of messages (conversation history)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate

        Returns:
            LLMResponse with generated text and usage stats

        Raises:
            Exception: If generation fails after retries
        """
        pass

    @abstractmethod
    async def close(self):
        """Close the client and cleanup resources."""
        pass
