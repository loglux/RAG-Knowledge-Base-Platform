"""Unit tests for the identifier-style query classifier."""

import pytest

from app.services.query_classifier import (
    DEFAULT_IDENTIFIER_LEXICAL_FLOOR,
    apply_lexical_floor,
    classify_query,
)


@pytest.mark.unit
class TestClassifyQuery:
    """classify_query should flag identifier-style queries and pass through the rest."""

    @pytest.mark.parametrize(
        "query,expected_match_substring",
        [
            # English identifier patterns
            ("Open Question 6 from EMA", "Question 6"),
            ("What's the answer to question 12?", "question 12"),
            ("Tell me about page 42", "page 42"),
            ("p. 100 of the textbook", "p. 100"),
            ("See Section 5.3 for details", "Section 5.3"),
            ("Subsection 1.2 covers boxplots", "Subsection 1.2"),
            ("Activity 14 instructions", "Activity 14"),
            ("Exercise 3 solution", "Exercise 3"),
            ("Unit 9 introduction", "Unit 9"),
            ("Chapter 2 summary", "Chapter 2"),
            ("TMA 03 cover page", "TMA 03"),
            ("Table 4 shows the data", "Table 4"),
            ("Figure 12 illustrates", "Figure 12"),
            ("Equation 7 derivation", "Equation 7"),
            ("§5.3 of the standard", "§5.3"),
            # Russian identifier patterns
            ("Вопрос 6 из EMA", "Вопрос 6"),
            ("Вопрос №3", "Вопрос №3"),
            ("страница 42", "страница 42"),
            ("Раздел 5.3", "Раздел 5.3"),
            ("Глава 7", "Глава 7"),
            ("Задание 4 решение", "Задание 4"),
            ("Таблица 3 содержит", "Таблица 3"),
            ("Рисунок 2 показывает", "Рисунок 2"),
        ],
    )
    def test_flags_identifier_queries(self, query, expected_match_substring):
        result = classify_query(query)
        assert result.is_identifier_query is True
        assert result.lexical_floor == DEFAULT_IDENTIFIER_LEXICAL_FLOOR
        assert (
            result.matched_pattern is not None
            and expected_match_substring.lower() in result.matched_pattern.lower()
        )

    @pytest.mark.parametrize(
        "query",
        [
            "what is antifragility",
            "explain how RAG works",
            "compare dense and sparse retrieval",
            "the question I have is about correlation",  # word "question" without number
            "что значит резильентность",
            "",
            "   ",
        ],
    )
    def test_does_not_flag_non_identifier_queries(self, query):
        result = classify_query(query)
        assert result.is_identifier_query is False
        assert result.lexical_floor is None
        assert result.matched_pattern is None

    def test_first_pattern_match_wins(self):
        """When multiple patterns match, the first one wins (deterministic ordering)."""
        # "Question 6" matches first; "page 8" matches a later pattern
        result = classify_query("Question 6 on page 8")
        assert result.is_identifier_query is True
        assert "question" in result.matched_pattern.lower()


@pytest.mark.unit
class TestApplyLexicalFloor:
    """apply_lexical_floor should only ever raise, never lower."""

    def test_none_floor_is_passthrough(self):
        assert apply_lexical_floor(0.3, None) == 0.3
        assert apply_lexical_floor(0.7, None) == 0.7

    def test_floor_raises_below_minimum(self):
        assert apply_lexical_floor(0.3, 0.7) == 0.7
        assert apply_lexical_floor(0.4, 0.7) == 0.7

    def test_floor_does_not_lower_higher_weight(self):
        # Caller already prefers strong lexical; floor must not weaken that.
        assert apply_lexical_floor(0.9, 0.7) == 0.9

    def test_equal_weights_are_idempotent(self):
        assert apply_lexical_floor(0.7, 0.7) == 0.7
