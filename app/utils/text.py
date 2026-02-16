"""Text processing utilities."""

import hashlib
from typing import List


def calculate_content_hash(content: str) -> str:
    """
    Calculate SHA-256 hash of content for deduplication.

    Args:
        content: Text content to hash

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: String to append if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def count_tokens_estimate(text: str) -> int:
    """
    Estimate token count for text.

    Simple heuristic: ~4 characters per token for English text.
    This is approximate and actual token count may vary.

    For accurate token counting, use tiktoken library (Phase 2+).

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    return len(text) // 4


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences (basic implementation).

    For MVP: Simple split on period + space.
    Future: Use more sophisticated sentence tokenization (NLTK, spaCy).

    Args:
        text: Text to split

    Returns:
        List of sentences
    """
    # Simple sentence splitting
    sentences = []
    current = []

    for char in text:
        current.append(char)
        if char in ".!?" and len(current) > 1:
            sentence = "".join(current).strip()
            if sentence:
                sentences.append(sentence)
            current = []

    # Add remaining text
    if current:
        sentence = "".join(current).strip()
        if sentence:
            sentences.append(sentence)

    return sentences


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.

    - Replace multiple spaces with single space
    - Replace multiple newlines with double newline
    - Strip leading/trailing whitespace

    Args:
        text: Text to normalize

    Returns:
        Normalized text
    """
    import re

    # Replace multiple spaces with single space
    text = re.sub(r" +", " ", text)

    # Replace multiple newlines with double newline
    text = re.sub(r"\n\n+", "\n\n", text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text
