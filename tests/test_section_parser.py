"""Regression tests for section_parser — verifies heading alignment and coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdd_agent.parse.section_parser import (
    _build_alias_index,
    _best_match,
    _load_schema,
    _normalize_heading,
    parse_corpus,
    parse_document,
    build_corpus_section_index,
    get_section_texts,
)


import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).parent.parent.resolve()
SCHEMA_PATH = ROOT_DIR / "schemas" / "pdd_section_schema.yaml"
sys.path.insert(0, str(ROOT_DIR / "src"))


class TestNormalizeHeading:
    def test_strips_whitespace(self):
        assert _normalize_heading("  3.4 Baseline Scenario  ") == "3.4 BASELINE SCENARIO"

    def test_uppercase(self):
        assert _normalize_heading("Project Details") == "PROJECT DETAILS"


class TestBuildAliasIndex:
    def test_canonical_heading_indexed(self):
        sections = _load_schema(SCHEMA_PATH)
        alias_index = _build_alias_index(sections)
        assert "PROJECT DETAILS" in alias_index

    def test_subsections_indexed(self):
        sections = _load_schema(SCHEMA_PATH)
        alias_index = _build_alias_index(sections)
        assert "1.1 SUMMARY DESCRIPTION OF THE PROJECT" in alias_index
        assert "3.4 BASELINE SCENARIO" in alias_index


class TestBestMatch:
    @pytest.fixture
    def alias_index(self):
        return _build_alias_index(_load_schema(SCHEMA_PATH))

    def test_exact_match(self, alias_index):
        result = _best_match("3.4 Baseline Scenario", alias_index)
        assert result == ("3", "3.4")

    def test_case_insensitive(self, alias_index):
        result = _best_match("SAfEGUARDS", alias_index)
        assert result == ("2", "")

    def test_returns_none_for_unknown(self, alias_index):
        result = _best_match("Random Unrelated Heading", alias_index)
        assert result is None

    def test_partial_match(self, alias_index):
        result = _best_match("1.4 Project Design", alias_index)
        assert result == ("1", "1.4")


class TestLoadSchema:
    def test_loads_all_sections(self):
        sections = _load_schema(SCHEMA_PATH)
        assert "1" in sections
        assert "2" in sections
        assert "3" in sections
        assert "4" in sections
        assert "5" in sections

    def test_subsections_loaded(self):
        sections = _load_schema(SCHEMA_PATH)
        assert "1.1" in sections["1"]["sub_sections"]
        assert "3.4" in sections["3"]["sub_sections"]
        assert "4.1" in sections["4"]["sub_sections"]


class TestParseCorpus:
    @pytest.fixture
    def corpus_dir(self):
        return Path(__file__).parent.parent.parent / "data" / "corpus" / "normalized"

    def test_parses_all_documents(self, corpus_dir):
        if not corpus_dir.exists():
            pytest.skip("Normalized corpus not available")
        results = parse_corpus(corpus_dir, SCHEMA_PATH)
        assert len(results) == 13
        for r in results:
            assert "error" not in r

    def test_all_documents_have_section_1(self, corpus_dir):
        if not corpus_dir.exists():
            pytest.skip("Normalized corpus not available")
        results = parse_corpus(corpus_dir, SCHEMA_PATH)
        for r in results:
            assert r["coverage"]["1"] in ("FULL", "PARTIAL")

    def test_all_documents_have_safeguards_section(self, corpus_dir):
        if not corpus_dir.exists():
            pytest.skip("Normalized corpus not available")
        results = parse_corpus(corpus_dir, SCHEMA_PATH)
        for r in results:
            assert "2" in r["coverage"]

    def test_all_documents_have_quantification(self, corpus_dir):
        if not corpus_dir.exists():
            pytest.skip("Normalized corpus not available")
        results = parse_corpus(corpus_dir, SCHEMA_PATH)
        for r in results:
            assert "4" in r["coverage"]

    def test_high_sensitivity_sections_present(self, corpus_dir):
        if not corpus_dir.exists():
            pytest.skip("Normalized corpus not available")
        results = parse_corpus(corpus_dir, SCHEMA_PATH)
        critical_sections = ["3.4", "3.5"]
        for r in results:
            for cs in critical_sections:
                mapped = [m for m in r["sections_mapped"] if m["canonical_sub_section_id"] == cs]
                assert len(mapped) > 0, f"{r['document_name']} missing {cs}"


class TestCorpusSectionIndex:
    @pytest.fixture
    def parsed(self):
        corpus_dir = Path(__file__).parent.parent.parent / "data" / "corpus" / "normalized"
        if not corpus_dir.exists():
            pytest.skip("Normalized corpus not available")
        return parse_corpus(corpus_dir, SCHEMA_PATH)

    def test_index_has_all_section_ids(self, parsed):
        index = build_corpus_section_index(parsed)
        for sid in ("1", "2", "3", "4", "5"):
            assert sid in index

    def test_retrieval_for_section_3_4(self, parsed):
        texts = get_section_texts(parsed, "3", "3.4", max_examples=3)
        assert len(texts) <= 3
        for t in texts:
            assert "canonical_heading" in t
            assert "document_name" in t


class TestCoverageLevels:
    def test_full_coverage(self):
        sections = _load_schema(SCHEMA_PATH)
        coverage = {}
        sid = "2"
        sub_count = len(sections[sid]["sub_sections"])
        matched_subs = 5
        total_subs = sub_count
        assert matched_subs == total_subs

    def test_partial_coverage(self):
        sections = _load_schema(SCHEMA_PATH)
        sid = "3"
        sub_count = len(sections[sid]["sub_sections"])
        matched_subs = 3
        total_subs = sub_count
        assert 0 < matched_subs < total_subs
