"""
Ollama LLM Service.

Handles text generation using Ollama API (local models).
"""
import logging
from typing import List, Optional
import httpx

from app.config import settings
from app.core.llm_base import (
    BaseLLMService,
    LLMProvider,
    Message,
    LLMResponse,
)


logger = logging.getLogger(__name__)


class OllamaLLMService(BaseLLMService):
    """
    Service for generating text using Ollama (local models).

    Features:
    - Async operations
    - Local model execution
    - Free (no API costs)
    - Supports streaming (optional)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
    ):
        """
        Initialize Ollama LLM service.

        Args:
            base_url: Ollama API base URL (uses settings.OLLAMA_BASE_URL if not provided)
            model: Model name (uses settings.OLLAMA_CHAT_MODEL if not provided)
            max_retries: Maximum number of retries for failed requests

        Raises:
            ValueError: If base URL is missing
        """
        # Ollama doesn't use API key (dummy value for base class)
        api_key = "local"
        model = model or settings.OLLAMA_CHAT_MODEL

        # Initialize base class with skip_validation for dynamic models
        super().__init__(api_key=api_key, model=model, max_retries=max_retries, skip_validation=True)

        self.base_url = base_url or settings.OLLAMA_BASE_URL
        if not self.base_url:
            raise ValueError("OLLAMA_BASE_URL is required for Ollama LLM service")

        timeout = httpx.Timeout(
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
            connect=10.0,
            read=settings.OLLAMA_TIMEOUT_SECONDS,
        )
        self.client = httpx.AsyncClient(timeout=timeout)  # Longer timeout for generation

        logger.info(f"Initialized OllamaLLMService with model: {self.model} at {self.base_url}")

    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate text completion using Ollama.

        Args:
            messages: List of messages (conversation history)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate (num_predict in Ollama)

        Returns:
            LLMResponse with generated text

        Raises:
            httpx.HTTPError: If Ollama API call fails
        """
        try:
            # Convert messages to Ollama format
            ollama_messages = [
                {
                    "role": msg.role,
                    "content": msg.content,
                }
                for msg in messages
            ]

            # Build request
            request_data = {
                "model": self.model,
                "messages": ollama_messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                }
            }

            if max_tokens:
                request_data["options"]["num_predict"] = max_tokens

            total_chars = sum(len(msg.content or "") for msg in messages)
            logger.debug(
                "Calling Ollama model=%s with %d messages (%d chars)",
                self.model,
                len(messages),
                total_chars,
            )

            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=request_data,
            )
            response.raise_for_status()

            data = response.json()

            # Extract response
            content = data.get("message", {}).get("content", "")

            # Ollama provides eval_count and prompt_eval_count
            input_tokens = data.get("prompt_eval_count")
            output_tokens = data.get("eval_count")

            logger.debug(
                f"Generated {len(content)} chars "
                f"(input: {input_tokens}, output: {output_tokens})"
            )

            return LLMResponse(
                content=content.strip(),
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=(input_tokens or 0) + (output_tokens or 0) if input_tokens and output_tokens else None,
            )

        except httpx.HTTPStatusError as e:
            body = None
            try:
                body = e.response.text
            except Exception:
                body = None
            logger.error(
                "Ollama API status error model=%s status=%s: %s",
                self.model,
                e.response.status_code if e.response else "unknown",
                (body[:1000] if body else "no response body"),
            )
            raise
        except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            logger.error("Ollama API timeout model=%s: %s", self.model, e)
            raise
        except httpx.HTTPError as e:
            logger.error("Ollama API error model=%s: %s", self.model, e)
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating text: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("OllamaLLMService closed")


# Singleton instance
_ollama_llm_service: Optional[OllamaLLMService] = None


def get_ollama_llm_service() -> OllamaLLMService:
    """
    Get or create singleton instance of OllamaLLMService.

    Returns:
        OllamaLLMService instance
    """
    global _ollama_llm_service

    if _ollama_llm_service is None:
        _ollama_llm_service = OllamaLLMService()

    return _ollama_llm_service


async def close_ollama_llm_service():
    """Close the singleton Ollama LLM service."""
    global _ollama_llm_service

    if _ollama_llm_service is not None:
        await _ollama_llm_service.close()
        _ollama_llm_service = None
