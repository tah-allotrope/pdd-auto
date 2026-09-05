"""Unit tests for corpus table lookup and plain-text extraction (PHASE-01).

Uses an inline fixture dict written to ``tmp_path`` — no real corpus needed,
no ``corpus`` marker.
"""

from __future__ import annotations

import json
from pathlib import Path

from pdd_agent.ingest.normalize import _extract_plain_text
from pdd_agent.ingest.table_lookup import find_tables, table_rows_as_pairs


def _write_norm(tmp_path: Path, stem: str, tables: list[dict]) -> Path:
    path = tmp_path / f"{stem}.norm.json"
    path.write_text(json.dumps({"tables": tables}), encoding="utf-8")
    return path


_FIXTURE_TABLES = [
    {
        "page": 3,
        "table_index": 0,
        "rows": [["Waste type", "Pn,j"], ["Paper and Cardboard", "2.7 %"]],
    }
]


class TestFindTables:
    def test_match_returns_table(self, tmp_path: Path):
        _write_norm(tmp_path, "doc_a", _FIXTURE_TABLES)
        found = find_tables("doc_a", ["Paper", "%"], normalized_dir=tmp_path)
        assert len(found) == 1
        assert found[0]["rows"][1][1] == "2.7 %"

    def test_missing_needle_returns_empty(self, tmp_path: Path):
        _write_norm(tmp_path, "doc_a", _FIXTURE_TABLES)
        assert find_tables("doc_a", ["Textiles"], normalized_dir=tmp_path) == []

    def test_missing_document_returns_empty_without_raise(self, tmp_path: Path):
        assert find_tables("missing_doc", ["x"], normalized_dir=tmp_path) == []


class TestTableRowsAsPairs:
    def test_pairs_skip_empty_key_cells(self):
        table = {"rows": [["Waste type", "Pn,j"], ["Food waste", "51.9 %"], ["", ""]]}
        assert table_rows_as_pairs(table) == [
            ("Waste type", "Pn,j"),
            ("Food waste", "51.9 %"),
        ]


class TestExtractPlainText:
    def test_headings_blocks_and_no_tables(self, tmp_path: Path):
        text_file = tmp_path / "a.txt"
        text_file.write_text("1. INTRODUCTION\nbody text\n2. SCOPE\nmore text\n", encoding="utf-8")
        result = _extract_plain_text(text_file)
        assert len(result["headings"]) == 2
        # NOTE (plan TASK-01-08 predicted 3): the implementation emits one block
        # per heading and skips the empty leading block, so this input yields 2.
        assert len(result["text_blocks"]) == 2
        assert result["tables"] == []
