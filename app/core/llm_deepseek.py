"""
DeepSeek LLM Service.

Uses OpenAI-compatible API with DeepSeek base_url.
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
from app.core.llm_base import BaseLLMService, Message, LLMResponse


logger = logging.getLogger(__name__)


class DeepSeekLLMService(BaseLLMService):
    """
    Service for generating text using DeepSeek (OpenAI-compatible) API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = 3,
    ):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI SDK is required for DeepSeek support")

        api_key = api_key or settings.DEEPSEEK_API_KEY
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in settings.")

        self.base_url = base_url or settings.DEEPSEEK_BASE_URL

        super().__init__(api_key=api_key, model=model or settings.DEEPSEEK_CHAT_MODEL, max_retries=max_retries)

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.base_url,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError, OpenAIError)),
        reraise=True,
    )
    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        try:
            chat_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

            requested_max_tokens = max_tokens or settings.DEEPSEEK_MAX_TOKENS
            # DeepSeek currently enforces max_tokens <= 8192 for chat completions.
            safe_max_tokens = min(requested_max_tokens, 8192) if requested_max_tokens else None

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=chat_messages,
                max_tokens=safe_max_tokens,
                temperature=temperature,
            )

            content = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "prompt_tokens", None)
            output_tokens = getattr(usage, "completion_tokens", None)
            total_tokens = getattr(usage, "total_tokens", None)
            cache_hit_tokens = getattr(usage, "prompt_cache_hit_tokens", None) if usage else None
            cache_miss_tokens = getattr(usage, "prompt_cache_miss_tokens", None) if usage else None

            logger.debug(
                "DeepSeek generated %s chars (input: %s, output: %s)",
                len(content),
                input_tokens,
                output_tokens,
            )

            return LLMResponse(
                content=content.strip(),
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cache_hit_tokens=cache_hit_tokens,
                cache_miss_tokens=cache_miss_tokens,
                cache_create_tokens=None,
            )

        except RateLimitError as e:
            logger.warning(f"Rate limit hit, will retry: {e}")
            raise
        except APITimeoutError as e:
            logger.warning(f"API timeout, will retry: {e}")
            raise
        except OpenAIError as e:
            logger.error(f"DeepSeek API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating text: {e}")
            raise

    async def close(self):
        await self.client.close()
        logger.info("DeepSeekLLMService closed")


_deepseek_service: Optional[DeepSeekLLMService] = None


def get_deepseek_service() -> DeepSeekLLMService:
    global _deepseek_service
    if _deepseek_service is None:
        _deepseek_service = DeepSeekLLMService()
    return _deepseek_service
