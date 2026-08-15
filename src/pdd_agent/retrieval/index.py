"""Local BM25 retrieval index backed by SQLite FTS5.

Build once, query many times. No external services, no embeddings API.
Index is stored at `data/index/corpus.fts.db` alongside the corpus.
"""

from __future__ import annotations

import structlog
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sqlite3
import yaml

logger = structlog.get_logger()

_SCHEMA_VERSION = "2"


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
        "document_family": row[8],
        "chunk_index": row[9],
    }


def load_corpus_families(path: Path | None = None) -> tuple[str, dict[str, str]]:
    """Load the document-stem -> methodology-family-slug mapping (ASM-003).

    Returns ``(default_family, mapping)``. Missing file -> ``("wte", {})``;
    never raises.
    """
    if path is None:
        path = Path(__file__).parent.parent.parent.parent / "configs" / "corpus_families.yaml"
    path = Path(path)

    if not path.exists():
        return "wte", {}

    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("corpus_families_load_failed", path=str(path), error=str(exc))
        return "wte", {}

    default_family = raw.get("default_family") or "wte"
    documents = raw.get("documents") or {}
    return default_family, documents


class RetrievalIndex:
    """SQLite FTS5 BM25 retrieval index over normalized corpus sections."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            db_path = (
                Path(__file__).parent.parent.parent.parent / "data" / "index" / "corpus.fts.db"
            )
        self._db_path = Path(db_path)
        # SQLite connections are bound to the thread that created them. The
        # service drafts sections from FastAPI BackgroundTasks worker threads,
        # so a single shared connection would raise sqlite3.ProgrammingError
        # ("SQLite objects created in a thread can only be used in that same
        # thread") for any thread other than the one that first called
        # _open(). threading.local() gives every calling thread its own
        # connection, created lazily on first use.
        self._local = threading.local()

    @property
    def db_path(self) -> Path:
        """Filesystem path of the SQLite database backing this index."""
        return self._db_path

    def _open(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self._db_path))
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            self._local.conn = conn
        return conn

    def build(
        self, normalized_dir: Path | None = None, schema_path: Path | None = None
    ) -> dict[str, Any]:
        """Walk the normalized corpus, extract text blocks, and index into FTS5."""
        from pdd_agent.parse.section_parser import _load_schema, parse_corpus

        if normalized_dir is None:
            normalized_dir = (
                Path(__file__).parent.parent.parent.parent / "data" / "corpus" / "normalized"
            )
        if schema_path is None:
            schema_path = (
                Path(__file__).parent.parent.parent.parent / "schemas" / "pdd_section_schema.yaml"
            )

        conn = self._open()

        conn.execute("DROP TABLE IF EXISTS sections_fts")
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

        parsed = parse_corpus(normalized_dir, schema_path)
        schema_sections = _load_schema(schema_path)
        default_family, family_map = load_corpus_families()

        def _classification(sid: str, ssid: str) -> tuple[str, str]:
            sec = schema_sections.get(sid, {})
            sub = sec.get("sub_sections", {}).get(ssid, {}) if ssid else {}
            content_class = sub.get("content_class") or sec.get("content_class") or ""
            review_sensitivity = (
                sub.get("review_sensitivity") or sec.get("review_sensitivity") or ""
            )
            return content_class, review_sensitivity

        docs_indexed = 0
        chunks_indexed = 0
        rows_by_document: dict[str, int] = {}

        for doc_result in parsed:
            if "error" in doc_result:
                logger.warning(
                    "skipping_doc", doc=doc_result.get("document_name"), error=doc_result["error"]
                )
                continue
            docs_indexed += 1
            doc_name = doc_result["document_name"]
            rows_by_document[doc_name] = 0
            family = family_map.get(doc_name, default_family)

            spans = doc_result.get("section_spans") or []
            if spans:
                for entry in spans:
                    sid = entry["canonical_section_id"]
                    ssid = entry.get("canonical_sub_section_id") or ""
                    heading = entry.get("canonical_heading", "")
                    text = entry.get("text", "")
                    if not text:
                        continue
                    content_class, review_sensitivity = _classification(sid, ssid)
                    conn.execute(
                        """
                        INSERT INTO sections_fts
                            (section_id, sub_section_id, document_name, canonical_heading, text,
                             content_class, review_sensitivity, document_family, chunk_index)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sid,
                            ssid,
                            doc_name,
                            heading,
                            text,
                            content_class,
                            review_sensitivity,
                            family,
                            entry.get("chunk_index", 0),
                        ),
                    )
                    chunks_indexed += 1
                    rows_by_document[doc_name] += 1
            else:
                for entry in doc_result.get("sections_mapped", []):
                    sid = entry["canonical_section_id"]
                    ssid = entry.get("canonical_sub_section_id") or ""
                    heading = entry.get("canonical_heading", "")
                    text_preview = entry.get("text_preview", "")
                    if not text_preview:
                        continue
                    text_snippet = text_preview[:500]
                    content_class, review_sensitivity = _classification(sid, ssid)
                    conn.execute(
                        """
                        INSERT INTO sections_fts
                            (section_id, sub_section_id, document_name, canonical_heading, text,
                             content_class, review_sensitivity, document_family, chunk_index)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sid,
                            ssid,
                            doc_name,
                            heading,
                            text_snippet,
                            content_class,
                            review_sensitivity,
                            family,
                            0,
                        ),
                    )
                    chunks_indexed += 1
                    rows_by_document[doc_name] += 1

        conn.execute("INSERT INTO sections_fts(sections_fts) VALUES('optimize')")
        conn.commit()

        docs_with_zero_sections = sorted(
            name for name, count in rows_by_document.items() if count == 0
        )
        for name in docs_with_zero_sections:
            logger.warning("corpus_document_yielded_no_sections", document=name)

        return {
            "docs_indexed": docs_indexed,
            "chunks_indexed": chunks_indexed,
            "db_path": str(self._db_path),
            "schema_version": _SCHEMA_VERSION,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "rows_by_document": rows_by_document,
            "docs_with_zero_sections": docs_with_zero_sections,
        }

    def search(
        self,
        query: str,
        section_id: str | None = None,
        content_class: str | None = None,
        document_family: str | None = None,
        k: int = 5,
    ) -> list[dict[str, Any]]:
        """BM25 full-text search with optional filters.

        Returns top-k chunks sorted by BM25 relevance, with document name,
        section heading, text preview, and relevance score.
        """
        conn = self._open()

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
        if document_family:
            where_parts.append("document_family = ?")
            args.append(document_family)

        where_clause = " AND " + " AND ".join(where_parts) if where_parts else ""

        sql = f"""
            SELECT rowid, section_id, sub_section_id, document_name,
                   canonical_heading, text, content_class, review_sensitivity,
                   document_family, chunk_index,
                   {rank} AS score
              FROM sections_fts
             WHERE sections_fts MATCH ?
             {where_clause}
             ORDER BY score
             LIMIT ?
        """
        rows = conn.execute(sql, [query, *args, k]).fetchall()
        return [_row_to_doc(row[:10]) | {"score": row[10]} for row in rows]

    def search_by_heading(
        self,
        heading: str,
        k: int = 3,
    ) -> list[dict[str, Any]]:
        """Find corpus chunks by near-exact heading match (no full-text needed)."""
        conn = self._open()

        pattern = f"%{heading}%"
        rows = conn.execute(
            """
            SELECT rowid, section_id, sub_section_id, document_name,
                   canonical_heading, text, content_class, review_sensitivity,
                   document_family, chunk_index
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
        document_family: str | None = None,
        k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve example text for a given section/sub-section across corpus docs."""
        conn = self._open()

        where_parts = ["section_id = ?"]
        args: list[Any] = [section_id]
        if sub_section_id:
            where_parts.append("sub_section_id = ?")
            args.append(sub_section_id)
        if document_family:
            where_parts.append("document_family = ?")
            args.append(document_family)

        where_clause = " AND ".join(where_parts)
        # One heading/sub-section can now yield several chunks per document (S-1
        # chunking), so a plain `ORDER BY document_name LIMIT k` can exhaust k on
        # the alphabetically-first document(s) alone. Rank rows within each
        # document by chunk_index first, so the top-k spans documents before it
        # takes a second chunk from the same one.
        rows = conn.execute(
            f"""
            WITH ranked AS (
                SELECT rowid, section_id, sub_section_id, document_name,
                       canonical_heading, text, content_class, review_sensitivity,
                       document_family, chunk_index,
                       ROW_NUMBER() OVER (
                           PARTITION BY document_name ORDER BY chunk_index
                       ) AS doc_rank
                  FROM sections_fts
                 WHERE {where_clause}
            )
            SELECT rowid, section_id, sub_section_id, document_name,
                   canonical_heading, text, content_class, review_sensitivity,
                   document_family, chunk_index
              FROM ranked
             ORDER BY doc_rank, document_name
             LIMIT ?
            """,
            [*args, k],
        ).fetchall()
        return [_row_to_doc(row) for row in rows]

    def stats(self) -> dict[str, Any]:
        """Return index statistics."""
        conn = self._open()
        row = conn.execute("SELECT COUNT(*) FROM sections_fts").fetchone()
        total = row[0] if row else 0
        row2 = conn.execute("SELECT COUNT(DISTINCT document_name) FROM sections_fts").fetchone()
        docs = row2[0] if row2 else 0
        return {
            "db_path": str(self._db_path),
            "total_chunks": total,
            "total_docs": docs,
            "schema_version": _SCHEMA_VERSION,
        }

    def close(self) -> None:
        """Close the calling thread's connection, if one was opened."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    def __enter__(self) -> "RetrievalIndex":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def is_built(self) -> bool:
        """Return True if the FTS table exists in the database."""
        conn = self._open()
        try:
            cur = conn.execute("SELECT COUNT(*) FROM sections_fts")
            cur.fetchone()
            return True
        except sqlite3.OperationalError:
            return False


def index_health(db_path: Path | None = None, corpus_dir: Path | None = None) -> dict[str, Any]:
    """Report retrieval-index coverage, duplication, and truncation metrics.

    Opens the database read-only. This is a manually-invoked diagnostic, not a
    consistency check: it reports whatever is committed at read time and adds
    no locking, so a report taken concurrently with a `build()` in another
    process may reflect a partially-written index (RISK-01-01).

    Returns ``{"error": "index not found", "db_path": str(path)}`` when the
    database file does not exist. Never raises.
    """
    if db_path is None:
        db_path = Path(__file__).parent.parent.parent.parent / "data" / "index" / "corpus.fts.db"
    path = Path(db_path)

    if not path.exists():
        return {"error": "index not found", "db_path": str(path)}

    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            total_row = conn.execute("SELECT COUNT(*) FROM sections_fts").fetchone()
            total_rows = total_row[0] if total_row else 0

            distinct_row = conn.execute("SELECT COUNT(DISTINCT text) FROM sections_fts").fetchone()
            distinct_texts = distinct_row[0] if distinct_row else 0

            duplication_rate = round(1 - distinct_texts / total_rows, 3) if total_rows else 0.0

            doc_rows = conn.execute(
                "SELECT document_name, COUNT(*) FROM sections_fts GROUP BY document_name"
            ).fetchall()
            rows_by_document = {name: count for name, count in doc_rows}

            lengths = sorted(
                len(row[0]) for row in conn.execute("SELECT text FROM sections_fts").fetchall()
            )
            n = len(lengths)
            mean_text_chars = round(sum(lengths) / n, 1) if n else 0.0
            if n == 0:
                median_text_chars = 0
            elif n % 2 == 1:
                median_text_chars = lengths[n // 2]
            else:
                median_text_chars = round((lengths[n // 2 - 1] + lengths[n // 2]) / 2)
            rows_at_500_chars = sum(1 for length in lengths if length == 500)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return {"error": str(exc), "db_path": str(path)}

    missing_documents: list[str] = []
    if corpus_dir is not None:
        corpus_stems = sorted(p.stem for p in Path(corpus_dir).glob("*.norm.json"))
        missing_documents = sorted(stem for stem in corpus_stems if stem not in rows_by_document)

    return {
        "db_path": str(path),
        "total_rows": total_rows,
        "distinct_texts": distinct_texts,
        "duplication_rate": duplication_rate,
        "documents": len(rows_by_document),
        "rows_by_document": rows_by_document,
        "mean_text_chars": mean_text_chars,
        "median_text_chars": median_text_chars,
        "rows_at_500_chars": rows_at_500_chars,
        "missing_documents": missing_documents,
    }


_index: RetrievalIndex | None = None


def get_retrieval_index() -> RetrievalIndex:
    """Return the process-wide retrieval index singleton.

    Precedence: the production ``corpus.fts.db`` wins when present. When it is
    absent but the bundled demo index ``demo.fts.db`` exists, the demo index is
    used so demo runs get corpus-backed provenance. Otherwise the default
    (unbuilt) corpus index is returned and retrieval degrades gracefully.
    """
    global _index
    if _index is None:
        index_dir = Path(__file__).parent.parent.parent.parent / "data" / "index"
        corpus_path = index_dir / "corpus.fts.db"
        demo_path = index_dir / "demo.fts.db"
        if not corpus_path.exists() and demo_path.exists():
            # Silent degradation here would ground a "corpus-backed" run on the
            # 3-document demo subset, so say so loudly.
            logger.warning(
                "retrieval_index_fallback",
                requested=str(corpus_path),
                using=str(demo_path),
            )
            _index = RetrievalIndex(db_path=demo_path)
        else:
            _index = RetrievalIndex()
    return _index


def get_active_index_path() -> Path:
    """Return the filesystem path of the retrieval index currently in use."""
    return get_retrieval_index().db_path


def get_active_index_doc_count() -> int:
    """Return the number of indexed section rows in the active retrieval index.

    Returns 0 when the index file does not exist or is not queryable, so callers
    can record grounding provenance without needing to handle sqlite errors.
    """
    import sqlite3

    path = get_active_index_path()
    if not path.exists():
        return 0
    try:
        conn = sqlite3.connect(str(path))
        try:
            return int(conn.execute("SELECT COUNT(*) FROM sections_fts").fetchone()[0])
        finally:
            conn.close()
    except sqlite3.Error:
        return 0


def set_retrieval_index(index: RetrievalIndex) -> None:
    """Override the process-wide retrieval index singleton.

    Used by ``demo_setup.build_demo_index()`` so a freshly built demo index is
    immediately used by any later retrieval calls in the same process.
    """
    global _index
    _index = index
