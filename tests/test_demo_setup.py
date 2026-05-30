"""Tests for the demo index builder (Sprint 3 PHASE-02)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdd_agent.demo_setup import DEMO_CORPUS_DIR, build_demo_index
from pdd_agent.retrieval.index import RetrievalIndex


def test_demo_corpus_dir_is_bundled():
    """The demo corpus subset ships in the repo."""
    assert DEMO_CORPUS_DIR.exists()
    norm_files = list(DEMO_CORPUS_DIR.glob("*.norm.json"))
    assert len(norm_files) >= 2


def test_build_demo_index_creates_queryable_index(tmp_path):
    """build_demo_index() produces a built FTS5 index from demo/corpus."""
    db_path = tmp_path / "demo.fts.db"
    index = build_demo_index(db_path=db_path)

    assert db_path.exists()
    assert index.is_built()

    stats = index.stats()
    assert stats["total_docs"] >= 2
    assert stats["total_chunks"] > 0
    index.close()


def test_build_demo_index_results_are_searchable(tmp_path):
    """The built demo index returns hits for a domain query."""
    db_path = tmp_path / "demo.fts.db"
    index = build_demo_index(db_path=db_path)

    hits = index.search("waste", k=5)
    assert len(hits) > 0
    assert all("document_name" in h for h in hits)
    index.close()


def test_build_demo_index_missing_corpus_raises(tmp_path):
    """A missing demo corpus directory raises a clear error."""
    with pytest.raises(FileNotFoundError):
        build_demo_index(
            demo_corpus_dir=tmp_path / "does-not-exist",
            db_path=tmp_path / "demo.fts.db",
        )
