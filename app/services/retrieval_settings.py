"""Helpers for resolving retrieval settings."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from app.config import settings
from app.models.database import AppSettings as AppSettingsModel
from app.models.database import KnowledgeBase as KnowledgeBaseModel
from app.models.enums import RetrievalMode
from app.models.schemas import RetrievalSettingsUpdate

logger = logging.getLogger(__name__)

BM25_FIELDS = (
    "bm25_match_mode",
    "bm25_min_should_match",
    "bm25_use_phrase",
    "bm25_analyzer",
)

RETRIEVAL_FIELDS = (
    "top_k",
    "retrieval_mode",
    "lexical_top_k",
    "hybrid_dense_weight",
    "hybrid_lexical_weight",
    "max_context_chars",
    "score_threshold",
    "use_structure",
    "use_mmr",
    "mmr_diversity",
    "context_expansion",
    "context_window",
    "rerank_enabled",
    "rerank_provider",
    "rerank_model",
    "rerank_candidate_pool",
    "rerank_top_n",
    "rerank_min_score",
)

ALL_RETRIEVAL_FIELDS = RETRIEVAL_FIELDS + BM25_FIELDS


def _default_retrieval_settings() -> Dict[str, Any]:
    return {
        "top_k": 5,
        "retrieval_mode": RetrievalMode.DENSE,
        "lexical_top_k": 20,
        "hybrid_dense_weight": 0.6,
        "hybrid_lexical_weight": 0.4,
        "max_context_chars": 0,
        "score_threshold": 0.0,
        "use_structure": False,
        "use_mmr": False,
        "mmr_diversity": 0.5,
        "context_expansion": None,
        "context_window": None,
        "rerank_enabled": False,
        "rerank_provider": "auto",
        "rerank_model": "rerank-2.5-lite",
        "rerank_candidate_pool": 20,
        "rerank_top_n": None,
        "rerank_min_score": None,
        "bm25_match_mode": settings.BM25_DEFAULT_MATCH_MODE,
        "bm25_min_should_match": settings.BM25_DEFAULT_MIN_SHOULD_MATCH,
        "bm25_use_phrase": settings.BM25_DEFAULT_USE_PHRASE,
        "bm25_analyzer": settings.BM25_DEFAULT_ANALYZER,
    }


def _apply_settings(
    target: Dict[str, Any], source: Dict[str, Any], fields: tuple[str, ...]
) -> None:
    for field in fields:
        if field in source and source[field] is not None:
            target[field] = source[field]


def _apply_settings_with_source(
    target: Dict[str, Any],
    explain: Dict[str, str],
    source: Dict[str, Any],
    fields: tuple[str, ...],
    source_name: str,
) -> None:
    for field in fields:
        if field in source and source[field] is not None:
            target[field] = source[field]
            explain[field] = source_name


def load_kb_retrieval_settings(kb: KnowledgeBaseModel) -> Dict[str, Any]:
    """Parse KB retrieval settings JSON into a dict."""
    if not kb.retrieval_settings_json:
        return {}
    try:
        raw = json.loads(kb.retrieval_settings_json)
    except Exception as exc:
        logger.warning("Invalid retrieval_settings_json on KB %s: %s", kb.id, exc)
        return {}
    try:
        validated = RetrievalSettingsUpdate(**raw)
        return validated.model_dump(exclude_none=True)
    except Exception as exc:
        logger.warning("Failed to validate KB retrieval settings %s: %s", kb.id, exc)
        return {}


def resolve_retrieval_settings(
    *,
    kb: KnowledgeBaseModel,
    app_settings: Optional[AppSettingsModel],
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Resolve effective retrieval settings.

    Precedence:
      1) explicit overrides
      2) KB retrieval_settings_json
      3) KB BM25 override columns
      4) app settings
      5) hard defaults
    """
    return resolve_retrieval_settings_scoped(
        kb=kb,
        app_settings=app_settings,
        conversation_overrides=None,
        request_overrides=overrides,
    )


def resolve_retrieval_settings_scoped(
    *,
    kb: KnowledgeBaseModel,
    app_settings: Optional[AppSettingsModel],
    conversation_overrides: Optional[Dict[str, Any]] = None,
    request_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Resolve effective retrieval settings with explicit scope precedence.

    Precedence (lowest -> highest):
      1) hard defaults
      2) app settings
      3) KB dedicated BM25 columns
      4) KB retrieval_settings_json
      5) conversation overrides (chat scope only)
      6) request overrides (current call)

    Non-retrieval fields are ignored.
    """
    resolved, _ = resolve_retrieval_settings_scoped_with_explain(
        kb=kb,
        app_settings=app_settings,
        conversation_overrides=conversation_overrides,
        request_overrides=request_overrides,
    )
    return resolved


def resolve_retrieval_settings_scoped_with_explain(
    *,
    kb: KnowledgeBaseModel,
    app_settings: Optional[AppSettingsModel],
    conversation_overrides: Optional[Dict[str, Any]] = None,
    request_overrides: Optional[Dict[str, Any]] = None,
) -> tuple[Dict[str, Any], Dict[str, str]]:
    """
    Same as resolve_retrieval_settings_scoped, but also returns per-field source map.
    """
    resolved = _default_retrieval_settings()
    explain: Dict[str, str] = {field: "defaults" for field in ALL_RETRIEVAL_FIELDS}

    if app_settings:
        app_values = {
            "top_k": app_settings.top_k,
            "retrieval_mode": app_settings.retrieval_mode,
            "lexical_top_k": app_settings.lexical_top_k,
            "hybrid_dense_weight": app_settings.hybrid_dense_weight,
            "hybrid_lexical_weight": app_settings.hybrid_lexical_weight,
            "max_context_chars": app_settings.max_context_chars,
            "score_threshold": app_settings.score_threshold,
            "use_structure": app_settings.use_structure,
            "rerank_enabled": app_settings.rerank_enabled,
            "rerank_provider": app_settings.rerank_provider,
            "rerank_model": app_settings.rerank_model,
            "rerank_candidate_pool": app_settings.rerank_candidate_pool,
            "rerank_top_n": app_settings.rerank_top_n,
            "rerank_min_score": app_settings.rerank_min_score,
            "bm25_match_mode": app_settings.bm25_match_mode,
            "bm25_min_should_match": app_settings.bm25_min_should_match,
            "bm25_use_phrase": app_settings.bm25_use_phrase,
            "bm25_analyzer": app_settings.bm25_analyzer,
        }
        _apply_settings_with_source(
            resolved, explain, app_values, ALL_RETRIEVAL_FIELDS, "app_settings"
        )

    kb_bm25 = {
        "bm25_match_mode": kb.bm25_match_mode,
        "bm25_min_should_match": kb.bm25_min_should_match,
        "bm25_use_phrase": kb.bm25_use_phrase,
        "bm25_analyzer": kb.bm25_analyzer,
    }
    _apply_settings_with_source(resolved, explain, kb_bm25, BM25_FIELDS, "kb_columns")

    kb_settings = load_kb_retrieval_settings(kb)
    _apply_settings_with_source(
        resolved, explain, kb_settings, ALL_RETRIEVAL_FIELDS, "kb_retrieval_settings"
    )

    if conversation_overrides:
        _apply_settings_with_source(
            resolved, explain, conversation_overrides, ALL_RETRIEVAL_FIELDS, "conversation_settings"
        )

    if request_overrides:
        _apply_settings_with_source(
            resolved, explain, request_overrides, ALL_RETRIEVAL_FIELDS, "request_overrides"
        )

    if resolved.get("retrieval_mode") is None:
        resolved["retrieval_mode"] = RetrievalMode.DENSE

    return resolved, explain
