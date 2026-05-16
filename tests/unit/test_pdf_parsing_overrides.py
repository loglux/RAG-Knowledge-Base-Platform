"""Unit tests for PDF parsing override plumbing."""

from types import SimpleNamespace

import pytest

from app.services.pdf_parsing_settings import _collect_overrides
from app.utils.file_handlers.pdf import OVERRIDABLE_PROFILE_FIELDS, PDFExtractionProfile


@pytest.mark.unit
class TestCollectOverrides:
    """_collect_overrides extracts only non-None PDF fields from a row/dict."""

    def test_none_source_yields_empty(self):
        assert _collect_overrides(None) == {}

    def test_orm_row_with_partial_values(self):
        row = SimpleNamespace(
            pdf_table_strategy="text",
            pdf_heading_size_sensitivity=None,
            pdf_min_doc_length=50,
        )
        out = _collect_overrides(row)
        assert out == {"table_strategy": "text", "min_doc_length": 50}

    def test_orm_row_all_none_yields_empty(self):
        row = SimpleNamespace(
            pdf_table_strategy=None,
            pdf_heading_size_sensitivity=None,
            pdf_min_doc_length=None,
        )
        assert _collect_overrides(row) == {}

    def test_dict_source(self):
        src = {
            "pdf_table_strategy": "lines",
            "pdf_heading_size_sensitivity": 1.25,
            "pdf_min_doc_length": None,
        }
        out = _collect_overrides(src)
        assert out == {"table_strategy": "lines", "size_ratio_threshold": 1.25}

    def test_ignores_unrelated_attrs(self):
        row = SimpleNamespace(
            pdf_table_strategy="lines",
            some_other_field="evil",
        )
        assert _collect_overrides(row) == {"table_strategy": "lines"}


@pytest.mark.unit
class TestPDFExtractionProfile:
    """PDFExtractionProfile accepts the documented override fields."""

    def test_defaults_match_documented_values(self):
        p = PDFExtractionProfile()
        assert p.table_strategy == "lines"
        assert p.size_ratio_threshold == 1.15
        assert p.min_doc_length == 100

    def test_default_zones_do_not_filter_anything(self):
        """No running headers/footers detected → no blanket top/bottom strip.

        Regression guard: an earlier version set header_zone_fraction=0.04 as
        a "just in case" default, which silently dropped real headings sitting
        in the top ~33 pt of pages (e.g. "Question N" labels in OU exam PDFs).
        The contract is now: the zones only filter when running headers were
        actually confirmed.
        """
        p = PDFExtractionProfile()
        assert p.header_zone_fraction == 0.0, (
            "header_zone_fraction default must be 0.0; non-zero default eats "
            "real top-of-page content in documents with no repeating headers"
        )
        assert (
            p.footer_zone_fraction == 1.0
        ), "footer_zone_fraction default must be 1.0 by the same reasoning"

    def test_can_construct_with_overrides(self):
        p = PDFExtractionProfile(
            table_strategy="text", size_ratio_threshold=1.25, min_doc_length=50
        )
        assert p.table_strategy == "text"
        assert p.size_ratio_threshold == 1.25
        assert p.min_doc_length == 50

    def test_overridable_field_names_match_profile_attributes(self):
        """Every name in OVERRIDABLE_PROFILE_FIELDS must be a real dataclass attribute.

        Catches typos in either place when someone adds a new tunable knob.
        """
        defaults = PDFExtractionProfile()
        for name in OVERRIDABLE_PROFILE_FIELDS:
            assert hasattr(
                defaults, name
            ), f"OVERRIDABLE_PROFILE_FIELDS lists '{name}' but PDFExtractionProfile has no such attribute"
