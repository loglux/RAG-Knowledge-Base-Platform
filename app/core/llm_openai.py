"""
OpenAI LLM Service.

Handles text generation using OpenAI GPT API.
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
    from openai import AsyncOpenAI, OpenAIError, RateLimitError, APITimeoutError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None
    OpenAIError = Exception
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


class OpenAILLMService(BaseLLMService):
    """
    Service for generating text using OpenAI GPT API.

    Features:
    - Async operations
    - Automatic retries with exponential backoff
    - Support for all GPT models
    - Proper message handling
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
    ):
        """
        Initialize OpenAI LLM service.

        Args:
            api_key: OpenAI API key (uses settings.OPENAI_API_KEY if not provided)
            model: Model name (uses settings.OPENAI_CHAT_MODEL if not provided)
            max_retries: Maximum number of retries for failed requests

        Raises:
            ImportError: If openai package is not installed
            ValueError: If API key is missing
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package is not installed. "
                "Install it with: pip install openai"
            )

        api_key = api_key or settings.OPENAI_API_KEY
        model = model or settings.OPENAI_CHAT_MODEL

        if not api_key:
            raise ValueError("OpenAI API key is required")

        # Initialize base class
        super().__init__(api_key=api_key, model=model, max_retries=max_retries, skip_validation=False)

        # Validate provider
        if self.model_config and self.provider != LLMProvider.OPENAI:
            raise ValueError(f"Model {model} is not an OpenAI model")

        self.client = AsyncOpenAI(api_key=self.api_key)

        logger.info(f"Initialized OpenAILLMService with model: {self.model}")

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
        Generate text completion using GPT.

        Args:
            messages: List of messages (conversation history)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate

        Returns:
            LLMResponse with generated text and usage stats

        Raises:
            OpenAIError: If OpenAI API call fails after retries
        """
        try:
            # Convert messages to OpenAI format
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            # Use Responses API for all OpenAI models.
            model_name = (self.model or "").lower()
            # Thinking models (gpt-5/o-series) do not support temperature.
            allow_temperature = not (model_name.startswith("gpt-5") or model_name.startswith("o"))

            response_kwargs = {
                "model": self.model,
                "input": openai_messages,
                "max_output_tokens": max_tokens or settings.OPENAI_MAX_TOKENS,
            }
            if allow_temperature:
                response_kwargs["temperature"] = temperature

            response = await self.client.responses.create(**response_kwargs)

            content = response.output_text or ""
            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "input_tokens", None)
            output_tokens = getattr(usage, "output_tokens", None)
            total_tokens = getattr(usage, "total_tokens", None)

            logger.debug(
                f"Generated {len(content)} chars "
                f"(input: {input_tokens}, output: {output_tokens})"
            )

            return LLMResponse(
                content=content.strip(),
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            )

        except RateLimitError as e:
            logger.warning(f"Rate limit hit, will retry: {e}")
            raise
        except APITimeoutError as e:
            logger.warning(f"API timeout, will retry: {e}")
            raise
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating text: {e}")
            raise

    async def close(self):
        """Close the OpenAI client."""
        await self.client.close()
        logger.info("OpenAILLMService closed")


# Singleton instance
_openai_service: Optional[OpenAILLMService] = None


def get_openai_service() -> OpenAILLMService:
    """
    Get or create singleton instance of OpenAILLMService.

    Returns:
        OpenAILLMService instance
    """
    global _openai_service

    if _openai_service is None:
        _openai_service = OpenAILLMService()

    return _openai_service


async def close_openai_service():
    """Close the singleton OpenAI service."""
    global _openai_service

    if _openai_service is not None:
        await _openai_service.close()
        _openai_service = None
