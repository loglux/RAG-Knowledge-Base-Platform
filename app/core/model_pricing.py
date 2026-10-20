"""
Live model pricing / context-window data, sourced from LiteLLM's
community-maintained cost map.

https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json

That file is free, public, MIT-licensed, and tracks ~4000+ models across
every major provider, each entry carrying a `source` pointing at the
provider's own pricing page it was transcribed from. We use it purely as a
correction/supplement to our hand-maintained catalogs (app.core.llm_base,
app.core.embeddings_base) - it corrects stale cost/context numbers on
models we already list, and enriches live-discovered-but-uncatalogued
models (app.core.model_discovery) with real pricing instead of leaving
them blank. It is never the sole source of truth: a model id absent from
both our catalog and this map is still shown with whatever our catalog has
(or with pricing omitted).
"""

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_PRICING_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
)
_CACHE_TTL_SECONDS = 24 * 60 * 60  # refresh at most once a day

_cache: Dict[str, Any] = {}
_cache_fetched_at: float = 0.0


async def get_litellm_pricing_map() -> Dict[str, Any]:
    """
    Return the cached LiteLLM pricing map, refetching at most once a day.

    On fetch failure, the previous successful cache (if any) keeps serving -
    a transient GitHub outage should degrade to "stale pricing", not "no
    pricing".

    Returns:
        Dict keyed by model id -> raw LiteLLM entry (input_cost_per_token,
        output_cost_per_token, max_input_tokens, ...). Empty dict if no
        fetch has ever succeeded.
    """
    global _cache, _cache_fetched_at

    if _cache and (time.time() - _cache_fetched_at) < _CACHE_TTL_SECONDS:
        return _cache

    try:
        import httpx

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(_PRICING_URL)
            response.raise_for_status()
            data = response.json()
            data.pop("sample_spec", None)  # schema-documentation placeholder entry
            _cache = data
            _cache_fetched_at = time.time()
            logger.info(f"Refreshed LiteLLM pricing map: {len(_cache)} entries")
    except Exception as e:
        logger.warning(f"Failed to refresh LiteLLM pricing map (serving stale/empty cache): {e}")

    return _cache


async def get_live_pricing(model_id: str) -> Optional[Dict[str, Optional[float]]]:
    """
    Look up live cost-per-million-tokens + context window for one model id.

    Args:
        model_id: Model id as used by the provider's own API (e.g. "gpt-5.1",
            "claude-sonnet-5")

    Returns:
        {"cost_per_million_input_tokens", "cost_per_million_output_tokens",
        "context_window"}, or None if the model isn't in the LiteLLM map.
    """
    entry = (await get_litellm_pricing_map()).get(model_id)
    if not entry:
        return None

    input_cost = entry.get("input_cost_per_token")
    output_cost = entry.get("output_cost_per_token")

    return {
        "cost_per_million_input_tokens": (
            input_cost * 1_000_000 if input_cost is not None else None
        ),
        "cost_per_million_output_tokens": (
            output_cost * 1_000_000 if output_cost is not None else None
        ),
        "context_window": entry.get("max_input_tokens") or entry.get("max_tokens"),
    }
