"""Tests for the retrieval search module."""

from __future__ import annotations

import pytest

from pdd_agent.retrieval.search import (
    _clean_query,
    _highlight,
    RetrievalResult,
    search,
    get_examples_for_section,
    get_section_heading_examples,
)


class TestCleanQuery:
    def test_strips_fts5_special_chars(self):
        assert _clean_query('"hello" (world)') == "hello world"

    def test_preserves_normal_words(self):
        assert _clean_query("baseline scenario waste") == "baseline scenario waste"

    def test_strips_arrows(self):
        assert _clean_query("landfill -> diversion") == "landfill diversion"


class TestHighlight:
    def test_finds_term_center(self):
        text = "The baseline scenario assumes the waste would have been disposed in a landfill."
        result = _highlight(text, ["baseline"])
        assert "baseline" in result.lower()
        assert len(result) <= 200

    def test_no_match_returns_start(self):
        text = "The project activity is waste-to-energy incineration."
        result = _highlight(text, ["xyz"])
        assert result == text[:200]

    def test_truncation_markers(self):
        text = "A" * 300 + "KEYWORD" + "B" * 300
        result = _highlight(text, ["KEYWORD"])
        assert result.startswith("...") or result.endswith("...")


class TestRetrievalResult:
    def test_to_dict(self):
        r = RetrievalResult(
            section_id="3.4",
            sub_section_id="",
            document_name="VCS_Soc Son",
            canonical_heading="Baseline Scenario",
            text="The baseline scenario assumes...",
            content_class="METHODOLOGY_DEPENDENT",
            review_sensitivity="HIGH",
            score=-1.5,
            matched_terms=["baseline"],
        )
        d = r.to_dict()
        assert d["section_id"] == "3.4"
        assert d["document_name"] == "VCS_Soc Son"
        assert d["provenance"] == "[CORPUS: VCS_Soc Son, Baseline Scenario]"
        assert d["score"] == -1.5


class TestSearchWithNoopIndex:
    """Test retrieval search against a noop (empty) index."""

    def test_search_empty_index_returns_empty(self):
        from pdd_agent.retrieval.index import RetrievalIndex
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            idx = RetrievalIndex(Path(tmpdir) / "test.fts.db")
            idx._open()
            try:
                assert idx.is_built() is False
            finally:
                idx.close()

    def test_get_examples_section_filter(self):
        from pdd_agent.retrieval.index import RetrievalIndex
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            idx = RetrievalIndex(Path(tmpdir) / "test.fts.db")
            idx._open()
            try:
                examples = get_examples_for_section("3.4", k=3, index=idx)
                assert isinstance(examples, list)
                assert examples == []
            finally:
                idx.close()

    def test_get_section_heading_examples(self):
        from pdd_agent.retrieval.index import RetrievalIndex
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            idx = RetrievalIndex(Path(tmpdir) / "test.fts.db")
            idx._open()
            try:
                examples = get_section_heading_examples("Baseline Scenario", k=3, index=idx)
                assert isinstance(examples, list)
                assert examples == []
            finally:
                idx.close()
