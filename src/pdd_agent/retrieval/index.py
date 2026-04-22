"""Local BM25 retrieval index backed by SQLite FTS5.

Build once, query many times. No external services, no embeddings API.
Index is stored at `data/index/corpus.fts.db` alongside the corpus.
"""

from __future__ import annotations

import json
import re
import structlog
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sqlite3

logger = structlog.get_logger()

_SCHEMA_VERSION = "1"


def _row_to_doc(row: tuple) -> dict[str, Any]:
    return {
        "rowid": row[0],
        "section_id": row[1],
        "sub_section_id": row[2],
        "document_name": row[3],
        "canonical_heading": row[4],
        "text": row[5],
        "content_class": row[6],
        "review_sensitivity": row[7],
    }


class RetrievalIndex:
    """SQLite FTS5 BM25 retrieval index over normalized corpus sections."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            db_path = (
                Path(__file__).parent.parent.parent.parent / "data" / "index" / "corpus.fts.db"
            )
        self._db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def _open(self) -> sqlite3.Connection:
        if self._conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA synchronous = NORMAL")
        return self._conn

    def build(
        self, normalized_dir: Path | None = None, schema_path: Path | None = None
    ) -> dict[str, Any]:
        """Walk the normalized corpus, extract text blocks, and index into FTS5."""
        from pdd_agent.parse.section_parser import parse_corpus

        if normalized_dir is None:
            normalized_dir = (
                Path(__file__).parent.parent.parent.parent / "data" / "corpus" / "normalized"
            )
        if schema_path is None:
            schema_path = (
                Path(__file__).parent.parent.parent.parent / "schemas" / "pdd_section_schema.yaml"
            )

        self._open()
        conn = self._conn
        assert conn is not None

        conn.execute("DROP TABLE IF EXISTS sections_fts")
        conn.execute(
            f"""
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

        parsed = parse_corpus(normalized_dir, schema_path)
        docs_indexed = 0
        chunks_indexed = 0

        for doc_result in parsed:
            if "error" in doc_result:
                logger.warning(
                    "skipping_doc", doc=doc_result.get("document_name"), error=doc_result["error"]
                )
                continue
            docs_indexed += 1
            for entry in doc_result.get("sections_mapped", []):
                sid = entry["canonical_section_id"]
                ssid = entry.get("canonical_sub_section_id") or ""
                heading = entry.get("canonical_heading", "")
                text_preview = entry.get("text_preview", "")
                if not text_preview:
                    continue
                text_snippet = text_preview[:500]
                conn.execute(
                    """
                    INSERT INTO sections_fts
                        (section_id, sub_section_id, document_name, canonical_heading, text, content_class, review_sensitivity)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (sid, ssid, doc_result["document_name"], heading, text_snippet, "", ""),
                )
                chunks_indexed += 1

        conn.execute("INSERT INTO sections_fts(sections_fts) VALUES('optimize')")
        conn.commit()

        return {
            "docs_indexed": docs_indexed,
            "chunks_indexed": chunks_indexed,
            "db_path": str(self._db_path),
            "schema_version": _SCHEMA_VERSION,
            "built_at": datetime.now(timezone.utc).isoformat(),
        }

    def search(
        self,
        query: str,
        section_id: str | None = None,
        content_class: str | None = None,
        k: int = 5,
    ) -> list[dict[str, Any]]:
        """BM25 full-text search with optional filters.

        Returns top-k chunks sorted by BM25 relevance, with document name,
        section heading, text preview, and relevance score.
        """
        self._open()
        conn = self._conn
        assert conn is not None

        if not query or not query.strip():
            return []

        rank = "bm25(sections_fts)"
        where_parts: list[str] = []
        args: list[Any] = []

        if section_id:
            where_parts.append("section_id = ?")
            args.append(section_id)
        if content_class:
            where_parts.append("content_class = ?")
            args.append(content_class)

        where_clause = "WHERE " + " AND ".join(where_parts) if where_parts else ""

        sql = f"""
            SELECT rowid, section_id, sub_section_id, document_name,
                   canonical_heading, text, content_class, review_sensitivity,
                   {rank} AS score
              FROM sections_fts
             WHERE sections_fts MATCH ?
             {where_clause}
             ORDER BY score
             LIMIT ?
        """
        rows = conn.execute(sql, [query, *args, k]).fetchall()
        return [_row_to_doc(row[:8]) | {"score": row[8]} for row in rows]

    def search_by_heading(
        self,
        heading: str,
        k: int = 3,
    ) -> list[dict[str, Any]]:
        """Find corpus chunks by near-exact heading match (no full-text needed)."""
        self._open()
        conn = self._conn
        assert conn is not None

        pattern = f"%{heading}%"
        rows = conn.execute(
            f"""
            SELECT rowid, section_id, sub_section_id, document_name,
                   canonical_heading, text, content_class, review_sensitivity
              FROM sections_fts
             WHERE canonical_heading LIKE ?
             ORDER BY document_name
             LIMIT ?
            """,
            [pattern, k],
        ).fetchall()
        return [_row_to_doc(row) for row in rows]

    def get_section_examples(
        self,
        section_id: str,
        sub_section_id: str | None = None,
        k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve example text for a given section/sub-section across corpus docs."""
        self._open()
        conn = self._conn
        assert conn is not None

        if sub_section_id:
            rows = conn.execute(
                """
                SELECT rowid, section_id, sub_section_id, document_name,
                       canonical_heading, text, content_class, review_sensitivity
                  FROM sections_fts
                 WHERE section_id = ? AND sub_section_id = ?
                 ORDER BY document_name
                 LIMIT ?
                """,
                [section_id, sub_section_id, k],
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT rowid, section_id, sub_section_id, document_name,
                       canonical_heading, text, content_class, review_sensitivity
                  FROM sections_fts
                 WHERE section_id = ?
                 ORDER BY document_name
                 LIMIT ?
                """,
                [section_id, k],
            ).fetchall()
        return [_row_to_doc(row) for row in rows]

    def stats(self) -> dict[str, Any]:
        """Return index statistics."""
        self._open()
        conn = self._conn
        assert conn is not None
        cur = conn.execute("SELECT COUNT(*) FROM sections_fts")
        total = cur.fetchone()[0] if cur.fetchone() else 0
        cur2 = conn.execute("SELECT COUNT(DISTINCT document_name) FROM sections_fts")
        docs = cur2.fetchone()[0] if cur2.fetchone() else 0
        return {
            "db_path": str(self._db_path),
            "total_chunks": total,
            "total_docs": docs,
            "schema_version": _SCHEMA_VERSION,
        }

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "RetrievalIndex":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def is_built(self) -> bool:
        """Return True if the FTS table exists in the database."""
        self._open()
        conn = self._conn
        assert conn is not None
        try:
            cur = conn.execute("SELECT COUNT(*) FROM sections_fts")
            cur.fetchone()
            return True
        except sqlite3.OperationalError:
            return False


_index: RetrievalIndex | None = None


def get_retrieval_index() -> RetrievalIndex:
    global _index
    if _index is None:
        _index = RetrievalIndex()
    return _index
