"""
Anthropic LLM Service.

Handles text generation using Anthropic Claude API.
"""
import logging
from typing import List, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

try:
    from anthropic import AsyncAnthropic, AnthropicError, RateLimitError, APITimeoutError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    AsyncAnthropic = None
    AnthropicError = Exception
    RateLimitError = Exception
    APITimeoutError = Exception

from app.config import settings
from app.core.llm_base import (
    BaseLLMService,
    LLMProvider,
    Message,
    LLMResponse,
)


logger = logging.getLogger(__name__)


class AnthropicLLMService(BaseLLMService):
    """
    Service for generating text using Anthropic Claude API.

    Features:
    - Async operations
    - Automatic retries with exponential backoff
    - Support for all Claude models
    - Proper system message handling
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
    ):
        """
        Initialize Anthropic LLM service.

        Args:
            api_key: Anthropic API key (uses settings.ANTHROPIC_API_KEY if not provided)
            model: Model name (uses settings.ANTHROPIC_CHAT_MODEL if not provided)
            max_retries: Maximum number of retries for failed requests

        Raises:
            ImportError: If anthropic package is not installed
            ValueError: If API key is missing
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package is not installed. "
                "Install it with: pip install anthropic"
            )

        api_key = api_key or settings.ANTHROPIC_API_KEY
        model = model or settings.ANTHROPIC_CHAT_MODEL

        if not api_key:
            raise ValueError("Anthropic API key is required")

        # Initialize base class
        super().__init__(api_key=api_key, model=model, max_retries=max_retries, skip_validation=False)

        # Validate provider
        if self.model_config and self.provider != LLMProvider.ANTHROPIC:
            raise ValueError(f"Model {model} is not an Anthropic model")

        self.client = AsyncAnthropic(api_key=self.api_key)

        logger.info(f"Initialized AnthropicLLMService with model: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
        reraise=True,
    )
    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate text completion using Claude.

        Args:
            messages: List of messages (conversation history)
            temperature: Sampling temperature (0-1 for Claude)
            max_tokens: Maximum tokens to generate

        Returns:
            LLMResponse with generated text and usage stats

        Raises:
            AnthropicError: If Anthropic API call fails after retries
        """
        try:
            # Separate system message from conversation
            system_message = None
            conversation_messages = []

            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    conversation_messages.append({
                        "role": msg.role,
                        "content": msg.content,
                    })

            # Call Anthropic API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or settings.ANTHROPIC_MAX_TOKENS,
                temperature=temperature,
                system=system_message,
                messages=conversation_messages,
            )

            # Extract content (Claude returns list of content blocks)
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            logger.debug(
                f"Generated {len(content)} chars "
                f"(input: {response.usage.input_tokens}, output: {response.usage.output_tokens})"
            )

            return LLMResponse(
                content=content.strip(),
                model=self.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

        except RateLimitError as e:
            logger.warning(f"Rate limit hit, will retry: {e}")
            raise
        except APITimeoutError as e:
            logger.warning(f"API timeout, will retry: {e}")
            raise
        except AnthropicError as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating text: {e}")
            raise

    async def close(self):
        """Close the Anthropic client."""
        await self.client.close()
        logger.info("AnthropicLLMService closed")


# Singleton instance
_anthropic_service: Optional[AnthropicLLMService] = None


def get_anthropic_service() -> AnthropicLLMService:
    """
    Get or create singleton instance of AnthropicLLMService.

    Returns:
        AnthropicLLMService instance
    """
    global _anthropic_service

    if _anthropic_service is None:
        _anthropic_service = AnthropicLLMService()

    return _anthropic_service


async def close_anthropic_service():
    """Close the singleton Anthropic service."""
    global _anthropic_service

    if _anthropic_service is not None:
        await _anthropic_service.close()
        _anthropic_service = None
