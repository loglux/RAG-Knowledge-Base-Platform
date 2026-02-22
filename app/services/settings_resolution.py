"""Helpers for scope-based settings resolution."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence
from uuid import UUID


def resolve_scoped_value(
    *,
    key: str,
    request_overrides: Mapping[str, Any],
    request_value: Any,
    conversation_overrides: Mapping[str, Any] | None = None,
    app_overrides: Mapping[str, Any] | None = None,
    fallback: Any = None,
) -> Any:
    """
    Resolve a setting value with deterministic precedence:
    request > conversation > app > fallback.
    """
    if key in request_overrides:
        return request_value
    if conversation_overrides and conversation_overrides.get(key) is not None:
        return conversation_overrides.get(key)
    if app_overrides and app_overrides.get(key) is not None:
        return app_overrides.get(key)
    return fallback


def parse_uuid_list(values: Optional[Sequence[Any]]) -> list[UUID]:
    """
    Parse a sequence into UUID list, skipping invalid entries.
    """
    if not values:
        return []
    parsed: list[UUID] = []
    for item in values:
        try:
            parsed.append(UUID(str(item)))
        except Exception:
            continue
    return parsed
