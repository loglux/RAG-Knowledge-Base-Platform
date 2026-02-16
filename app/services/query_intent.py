"""
Query Intent Extraction Service.

Uses LLM to understand user query intent for structured search.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

from pydantic import BaseModel

from app.config import settings
from app.core.llm_base import Message
from app.core.llm_factory import create_llm_service

logger = logging.getLogger(__name__)


class QueryIntent(BaseModel):
    """Extracted intent from user query."""

    intent_type: str  # "structured_search", "semantic_search", "unknown"
    document_name: Optional[str] = None  # e.g., "TMA01", "Unit 3"
    section_type: Optional[str] = None  # e.g., "question", "section", "chapter"
    section_number: Optional[int] = None  # e.g., 2 for "Question 2"
    section_id: Optional[str] = None  # e.g., "1.2" for "Section 1.2"
    confidence: float = 0.0  # 0.0 to 1.0
    original_query: str


class QueryIntentExtractor:
    """Service for extracting structured intent from natural language queries."""

    EXTRACTION_PROMPT = """Analyze this user query and extract structured search intent.

User Query: "{query}"

Available documents in knowledge base:
{document_list}

Your task:
Determine if the user is asking for a specific structural element (like a question, section, or chapter) or if this is a general semantic search.

Return JSON with:
- intent_type: "structured_search" if asking for specific question/section/chapter, otherwise "semantic_search"
- document_name: exact document identifier mentioned in the query (must match one of the provided document names) or null
- section_type: "question", "section", "chapter", or null
- section_number: number if mentioned (e.g., 2 for "Question 2") or null
- section_id: section identifier like "1.2" for hierarchical sections, or null
- confidence: 0.0-1.0 how confident you are this is structured search

Return ONLY valid JSON, no other text."""

    async def extract_intent(
        self, query: str, kb_documents: list[str] = None, use_cache: bool = True
    ) -> QueryIntent:
        """
        Extract structured intent from user query using LLM.

        Args:
            query: User's search query
            kb_documents: List of document names in KB (for context)
            use_cache: Whether to use simple pattern matching as fallback

        Returns:
            QueryIntent with extracted information
        """
        # LLM-based extraction (more accurate, slower)
        try:
            doc_list = "\n".join([f"- {doc}" for doc in (kb_documents or [])])

            llm_service = create_llm_service(model="claude-haiku-4-5-20251001")  # Fast, cheap

            prompt = self.EXTRACTION_PROMPT.format(
                query=query, document_list=doc_list or "- (no document list provided)"
            )

            response = await llm_service.generate(
                messages=[
                    Message(
                        role="system",
                        content="You are a query intent analyzer. Return only valid JSON.",
                    ),
                    Message(role="user", content=prompt),
                ],
                temperature=settings.QUERY_INTENT_LLM_TEMPERATURE,
            )

            # Parse JSON response
            intent_data = self._parse_llm_response(response.content)

            intent = QueryIntent(
                intent_type=intent_data.get("intent_type", "semantic_search"),
                document_name=intent_data.get("document_name"),
                section_type=intent_data.get("section_type"),
                section_number=intent_data.get("section_number"),
                section_id=intent_data.get("section_id"),
                confidence=intent_data.get("confidence", 0.5),
                original_query=query,
            )

            logger.info(f"LLM extracted intent: {intent.model_dump()}")
            await llm_service.close()

            return intent

        except Exception as e:
            logger.error(f"Intent extraction failed: {e}")
            # Fallback to semantic search
            return QueryIntent(intent_type="semantic_search", confidence=1.0, original_query=query)

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM JSON response."""
        # Try to extract JSON from response
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response

        try:
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response: {response[:500]}")
            return {"intent_type": "semantic_search", "confidence": 1.0}


# Singleton
_extractor: Optional[QueryIntentExtractor] = None


def get_query_intent_extractor() -> QueryIntentExtractor:
    """Get or create singleton instance."""
    global _extractor
    if _extractor is None:
        _extractor = QueryIntentExtractor()
    return _extractor
