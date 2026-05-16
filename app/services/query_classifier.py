"""Detect identifier-style queries and recommend a lexical-weighted retrieval blend.

The hybrid retriever blends dense (semantic) and lexical (BM25) scores at a
fixed ratio. That ratio is tuned for paraphrase / "explain X" queries where
semantic similarity carries most of the signal. Identifier-style queries
("Question 6 from EMA", "Раздел 5.3", "Activity 14", "page 42") behave the
opposite way: the literal token is the strongest signal and the surrounding
chunk content is often topically unrelated to the query phrasing, so the
default dense weight drags the right chunk below front-matter / introduction
chunks in the final ranking.

This module is a single-function classifier: given a query string, return a
``lexical_floor`` — a minimum value for ``hybrid_lexical_weight`` that the
retriever should apply for this query. The caller is responsible for taking
``max(current_weight, floor)``; the classifier never lowers a higher
user-set weight.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Sequence

# Identifier patterns that, when present, indicate a "find by identifier"
# query. Compiled once at module load.
#
# Each pattern is conservative — it should match phrasings that *only* make
# sense as an identifier ("Question 6 from EMA"), not phrasings where the
# same surface form is incidental ("the question that was asked 6 times").
# False positives waste a query by lifting lexical weight unnecessarily; the
# cost is small (slightly worse ranking on that one query) so we err
# towards matching.
_IDENTIFIER_PATTERNS: Sequence[re.Pattern] = (
    # English: Question 6, Question 6(a), Question 6 from ...
    re.compile(r"\bquestion\s+\d+", re.IGNORECASE),
    # Russian: вопрос 6, Вопрос №6
    re.compile(r"\bвопрос[у-яё]*\s*№?\s*\d+", re.IGNORECASE),
    # English/Russian: page 42, страница 42, стр. 42, p. 42
    re.compile(r"\b(?:page|страниц[аеуы]|стр\.?|p\.)\s*\d+", re.IGNORECASE),
    # Section / Subsection N or N.N — "Section 5.3", "Subsection 5.3"
    re.compile(r"\b(?:sub)?section\s+\d+(?:\.\d+)*", re.IGNORECASE),
    # Russian: раздел 5, подраздел 5.3, глава 7
    re.compile(r"\b(?:раздел|подраздел|глава|параграф)\s*\d+(?:\.\d+)*", re.IGNORECASE),
    # OU/edu coursework labels: Activity 14, Exercise 3, Unit 9, Chapter 2,
    # TMA 03, EMA, Task 5
    re.compile(
        r"\b(?:activity|exercise|unit|chapter|задание|упражнение|tma|ema|task)\s*\d+",
        re.IGNORECASE,
    ),
    # Tables / Figures / Equations: "Table 4", "Figure 12", "Eq. 3"
    re.compile(
        r"\b(?:table|figure|fig\.?|equation|eq\.?|таблиц[аеу]|рис(?:унок|\.)?|формул[аеу])\s*\d+",
        re.IGNORECASE,
    ),
    # Bare numbered references: §5.3, §7
    re.compile(r"§\s*\d+(?:\.\d+)*"),
)


# When an identifier is present, push lexical weight up to this floor.
# Chosen so that for a typical request payload (dense_weight=0.6,
# lexical_weight=0.4) the identifier chunk's strong BM25 signal can
# overcome the dense score advantage of front-matter chunks (empirically
# ~0.30 dense advantage on the "Question 6 from EMA" case).
DEFAULT_IDENTIFIER_LEXICAL_FLOOR: float = 0.7


@dataclass(frozen=True)
class QueryClassification:
    """Result of running the classifier over a query string.

    ``is_identifier_query`` is the headline flag. ``lexical_floor`` is what
    the caller should pass to the retriever (``None`` means "no adjustment,
    use the supplied weight as-is"). ``matched_pattern`` is the literal
    substring that triggered the classification — kept for logging and
    debugging.
    """

    is_identifier_query: bool
    lexical_floor: Optional[float]
    matched_pattern: Optional[str]


def classify_query(query: str) -> QueryClassification:
    """Run identifier-pattern detection over a query string.

    Returns a ``QueryClassification``; never raises. An empty / whitespace
    query yields a non-identifier classification.
    """
    if not query or not query.strip():
        return QueryClassification(False, None, None)

    for pattern in _IDENTIFIER_PATTERNS:
        match = pattern.search(query)
        if match:
            return QueryClassification(
                is_identifier_query=True,
                lexical_floor=DEFAULT_IDENTIFIER_LEXICAL_FLOOR,
                matched_pattern=match.group(0),
            )

    return QueryClassification(False, None, None)


def apply_lexical_floor(current_lexical_weight: float, floor: Optional[float]) -> float:
    """Compute the effective lexical weight after applying an optional floor.

    Returns ``current_lexical_weight`` unchanged if ``floor`` is ``None`` or
    not greater than the current weight. Never lowers a higher user-set
    weight — the caller's explicit setting always wins when it is already
    above the floor.
    """
    if floor is None:
        return current_lexical_weight
    return max(current_lexical_weight, floor)
