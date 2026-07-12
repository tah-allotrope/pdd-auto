"""Thread-safety tests for RetrievalIndex (service drafts from worker threads)."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from pdd_agent.retrieval.index import RetrievalIndex


@pytest.fixture()
def built_index(tmp_path: Path) -> RetrievalIndex:
    normalized_dir = tmp_path / "normalized"
    normalized_dir.mkdir()
    index = RetrievalIndex(db_path=tmp_path / "test.fts.db")
    # Build directly against the FTS table rather than the full parse_corpus
    # pipeline — this test only cares about connection thread-safety.
    conn = index._open()
    conn.execute("DROP TABLE IF EXISTS sections_fts")
    conn.execute(
        """
        CREATE VIRTUAL TABLE sections_fts USING fts5(
            section_id, sub_section_id, document_name, canonical_heading,
            text, content_class, review_sensitivity,
            tokenize='porter unicode61'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO sections_fts
            (section_id, sub_section_id, document_name, canonical_heading, text, content_class, review_sensitivity)
        VALUES ('3', '3.3', 'test_doc', 'Project Boundary',
                'waste incineration facility project boundary', '', '')
        """
    )
    conn.commit()
    return index


class TestThreadSafety:
    def test_search_from_multiple_threads_does_not_raise(self, built_index: RetrievalIndex):
        def run_search() -> list[dict]:
            return built_index.search("waste incineration")

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(run_search) for _ in range(8)]
            results = [f.result() for f in futures]

        for result in results:
            assert len(result) == 1
            assert result[0]["document_name"] == "test_doc"

        # All threads should have returned identical results.
        first = results[0]
        assert all(r == first for r in results)

    def test_each_thread_gets_its_own_connection(self, built_index: RetrievalIndex):
        seen_conn_ids = set()
        lock_free_ids: list[int] = []

        def record_conn_id() -> None:
            conn = built_index._open()
            lock_free_ids.append(id(conn))

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(record_conn_id) for _ in range(4)]
            for f in futures:
                f.result()

        # Each worker thread should have created a distinct connection object.
        assert len(set(lock_free_ids)) == len(lock_free_ids)

    def test_main_thread_connection_still_usable_after_worker_threads(
        self, built_index: RetrievalIndex
    ):
        def run_search() -> None:
            built_index.search("waste incineration")

        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda _: run_search(), range(4)))

        # The connection opened lazily on the main thread (this test method)
        # must still work and must not be a worker thread's closed connection.
        result = built_index.search("waste incineration")
        assert len(result) == 1

    def test_close_only_closes_calling_threads_connection(self, built_index: RetrievalIndex):
        # Open a connection on a worker thread, close it there, then confirm
        # the main-thread connection (opened by the fixture) is unaffected.
        def open_and_close() -> None:
            built_index._open()
            built_index.close()

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(open_and_close).result()

        # Main-thread connection (from the fixture's _open() call) should
        # still be open and usable.
        result = built_index.search("waste incineration")
        assert len(result) == 1
