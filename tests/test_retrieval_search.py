"""Tests for the retrieval search module."""

from __future__ import annotations

import json
import sqlite3

import structlog.testing

from pdd_agent.retrieval.search import (
    _clean_query,
    _highlight,
    RetrievalResult,
    get_examples_for_section,
    get_section_heading_examples,
    search,
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


def _make_fts_db(path, rows):
    """Create a minimal ``sections_fts`` table at `path` with the given rows.

    Each row is a 7-tuple matching the FTS5 column order used by
    ``RetrievalIndex.build()``: (section_id, sub_section_id, document_name,
    canonical_heading, text, content_class, review_sensitivity).
    """
    conn = sqlite3.connect(str(path))
    conn.execute(
        """
        CREATE VIRTUAL TABLE sections_fts USING fts5(
            section_id,
            sub_section_id,
            document_name,
            canonical_heading,
            text,
            content_class,
            review_sensitivity,
            tokenize='porter unicode61'
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO sections_fts
            (section_id, sub_section_id, document_name, canonical_heading, text, content_class, review_sensitivity)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    conn.close()


class TestIndexHealth:
    """Tests for `pdd_agent.retrieval.index.index_health()`."""

    def test_duplication_rate(self, tmp_path):
        from pdd_agent.retrieval.index import index_health

        db_path = tmp_path / "health.fts.db"
        _make_fts_db(
            db_path,
            [
                ("1", "", "doc-a", "Heading", "AAA", "", ""),
                ("1", "", "doc-a", "Heading", "AAA", "", ""),
                ("1", "", "doc-a", "Heading", "AAA", "", ""),
                ("2", "", "doc-a", "Heading", "BBB", "", ""),
            ],
        )

        report = index_health(db_path=db_path)

        assert report["total_rows"] == 4
        assert report["distinct_texts"] == 2
        assert report["duplication_rate"] == 0.5

    def test_missing_db_returns_error_without_raising(self, tmp_path):
        from pdd_agent.retrieval.index import index_health

        report = index_health(db_path=tmp_path / "does-not-exist.db")

        assert report["error"] == "index not found"

    def test_empty_index_no_zero_division(self, tmp_path):
        from pdd_agent.retrieval.index import index_health

        db_path = tmp_path / "empty.fts.db"
        _make_fts_db(db_path, [])

        report = index_health(db_path=db_path)

        assert report["total_rows"] == 0
        assert report["duplication_rate"] == 0.0

    def test_missing_documents_against_corpus_dir(self, tmp_path):
        from pdd_agent.retrieval.index import index_health

        corpus_dir = tmp_path / "normalized"
        corpus_dir.mkdir()
        (corpus_dir / "alpha.norm.json").write_text("{}", encoding="utf-8")
        (corpus_dir / "beta.norm.json").write_text("{}", encoding="utf-8")

        db_path = tmp_path / "health.fts.db"
        # Mirror the document_name RetrievalIndex.build() actually stores:
        # Path("alpha.norm.json").stem == "alpha.norm".
        _make_fts_db(
            db_path,
            [("1", "", "alpha.norm", "Heading", "some indexed text", "", "")],
        )

        report = index_health(db_path=db_path, corpus_dir=corpus_dir)

        assert report["missing_documents"] == ["beta.norm"]

    def test_rows_at_500_and_median(self, tmp_path):
        from pdd_agent.retrieval.index import index_health

        db_path = tmp_path / "health.fts.db"
        _make_fts_db(
            db_path,
            [
                ("1", "", "doc-a", "Heading", "x" * 500, "", ""),
                ("1", "", "doc-a", "Heading", "y" * 500, "", ""),
                ("1", "", "doc-a", "Heading", "z" * 120, "", ""),
            ],
        )

        report = index_health(db_path=db_path)

        assert report["rows_at_500_chars"] == 2
        assert report["median_text_chars"] == 500


def _make_fts_db_v2(path, rows):
    """Create a `sections_fts` table at `path` including the PHASE-02 columns.

    Each row is a 9-tuple: (section_id, sub_section_id, document_name,
    canonical_heading, text, content_class, review_sensitivity,
    document_family, chunk_index) — matching the FTS5 column order used by
    ``RetrievalIndex.build()`` after PHASE-02.
    """
    conn = sqlite3.connect(str(path))
    conn.execute(
        """
        CREATE VIRTUAL TABLE sections_fts USING fts5(
            section_id,
            sub_section_id,
            document_name,
            canonical_heading,
            text,
            content_class,
            review_sensitivity,
            document_family,
            chunk_index,
            tokenize='porter unicode61'
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO sections_fts
            (section_id, sub_section_id, document_name, canonical_heading, text,
             content_class, review_sensitivity, document_family, chunk_index)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    conn.close()


class TestDocumentFamilyFilter:
    """Tests for the `document_family` filter and its ASM-004 fallback."""

    def test_family_filter_restricts_results(self, tmp_path):
        from pdd_agent.retrieval.index import RetrievalIndex

        db_path = tmp_path / "family.fts.db"
        _make_fts_db_v2(
            db_path,
            [
                ("1", "", "alpha", "Heading", "waste management text alpha", "", "", "wte", 0),
                ("1", "", "beta", "Heading", "waste management text beta", "", "", "rice", 0),
            ],
        )

        idx = RetrievalIndex(db_path=db_path)
        try:
            results = idx.search("waste", document_family="rice")
            assert results
            assert all(r["document_name"] == "beta" for r in results)
        finally:
            idx.close()

    def test_family_fallback_when_filtered_search_empty(self, tmp_path):
        from pdd_agent.retrieval.index import RetrievalIndex

        db_path = tmp_path / "fallback.fts.db"
        _make_fts_db_v2(
            db_path,
            [
                (
                    "1",
                    "",
                    "alpha",
                    "Heading",
                    "termpresentonlyinwte content",
                    "",
                    "",
                    "wte",
                    0,
                ),
            ],
        )

        idx = RetrievalIndex(db_path=db_path)
        try:
            with structlog.testing.capture_logs() as logs:
                results = search("termpresentonlyinwte", document_family="rice", index=idx)
            assert len(results) > 0
            assert any(entry.get("event") == "retrieval_family_fallback" for entry in logs)
        finally:
            idx.close()

    def test_content_class_filter_returns_results(self, tmp_path):
        """Regression: content_class was always inserted as "" (index.py:126),
        so a content_class filter always returned zero results. PHASE-02 fixes
        the population, so this filter must now find a matching row."""
        from pdd_agent.retrieval.index import RetrievalIndex

        db_path = tmp_path / "content_class.fts.db"
        _make_fts_db_v2(
            db_path,
            [
                (
                    "3",
                    "3.2",
                    "doc",
                    "Applicability",
                    "waste applicability conditions text",
                    "METHODOLOGY_DEPENDENT",
                    "HIGH",
                    "wte",
                    0,
                ),
            ],
        )

        idx = RetrievalIndex(db_path=db_path)
        try:
            results = idx.search("waste", content_class="METHODOLOGY_DEPENDENT")
            assert len(results) >= 1
        finally:
            idx.close()


class TestRetrievalIndexBuildStats:
    """Tests for the `rows_by_document` / `docs_with_zero_sections` build() stats."""

    def test_zero_yield_document_reported(self, tmp_path):
        from pdd_agent.retrieval.index import RetrievalIndex

        corpus_dir = tmp_path / "normalized"
        corpus_dir.mkdir()
        norm_doc = {
            "headings": [
                {"text": "Zzyzx9945 Nonexistent Placeholder Heading", "level": 1, "page": 1}
            ],
            "pages": [
                {
                    "page": 1,
                    "text": "Zzyzx9945 Nonexistent Placeholder Heading\nBody text.",
                }
            ],
            "text_blocks": [],
        }
        (corpus_dir / "onlydoc.norm.json").write_text(json.dumps(norm_doc), encoding="utf-8")

        idx = RetrievalIndex(db_path=tmp_path / "index.fts.db")
        try:
            stats = idx.build(normalized_dir=corpus_dir)
        finally:
            idx.close()

        assert "onlydoc.norm" in stats["docs_with_zero_sections"]
        assert stats["rows_by_document"]["onlydoc.norm"] == 0
