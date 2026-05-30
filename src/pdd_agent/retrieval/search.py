"""Query-time BM25 retrieval with section filtering and result ranking.

Uses the SQLite FTS5 index built by `index.py`. Supports filtering by
section_id, sub_section_id, content_class, and document_name.
"""

from __future__ import annotations

import re
import structlog
from pathlib import Path
from typing import Any

from pdd_agent.retrieval.index import RetrievalIndex, get_retrieval_index

logger = structlog.get_logger()


DEFAULT_K = 5
MAX_K = 50

_INDEX_WARNING_SHOWN = False


def _warn_no_index_once() -> None:
    """Emit a single degraded-mode warning per process when no index is built."""
    global _INDEX_WARNING_SHOWN
    if _INDEX_WARNING_SHOWN:
        return
    _INDEX_WARNING_SHOWN = True
    logger.warning(
        "retrieval_index_unavailable",
        message=(
            "Retrieval index not available — running without corpus-backed "
            "provenance. Run 'pdd-agent demo-setup' to build a demo index."
        ),
    )


def _clean_query(query: str) -> str:
    """Strip special FTS5 operators and extra whitespace."""
    text = re.sub(r'["\(\)\-*>]', " ", query.strip())
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _highlight(text: str, terms: list[str], max_len: int = 200) -> str:
    """Return a short excerpt centered on the first matching term."""
    text_lower = text.lower()
    first_pos = -1
    for term in terms:
        pos = text_lower.find(term.lower())
        if pos >= 0:
            first_pos = pos
            break
    if first_pos < 0:
        return text[:max_len]
    start = max(0, first_pos - 60)
    end = min(len(text), first_pos + max_len - 60)
    excerpt = text[start:end]
    return ("..." if start > 0 else "") + excerpt + ("..." if end < len(text) else "")


class RetrievalResult:
    """Structured retrieval result with provenance metadata."""

    def __init__(
        self,
        section_id: str,
        sub_section_id: str,
        document_name: str,
        canonical_heading: str,
        text: str,
        content_class: str,
        review_sensitivity: str,
        score: float,
        matched_terms: list[str],
    ) -> None:
        self.section_id = section_id
        self.sub_section_id = sub_section_id
        self.document_name = document_name
        self.canonical_heading = canonical_heading
        self.text = text
        self.content_class = content_class
        self.review_sensitivity = review_sensitivity
        self.score = score
        self.matched_terms = matched_terms

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "sub_section_id": self.sub_section_id,
            "document_name": self.document_name,
            "canonical_heading": self.canonical_heading,
            "text": self.text,
            "content_class": self.content_class,
            "review_sensitivity": self.review_sensitivity,
            "score": self.score,
            "matched_terms": self.matched_terms,
            "provenance": f"[CORPUS: {self.document_name}, {self.canonical_heading}]",
        }

    def __repr__(self) -> str:
        return f"<RetrievalResult {self.section_id}/{self.sub_section_id} from {self.document_name} score={self.score:.3f}>"


def search(
    query: str,
    section_id: str | None = None,
    content_class: str | None = None,
    k: int = DEFAULT_K,
    index: RetrievalIndex | None = None,
) -> list[RetrievalResult]:
    """Run BM25 search against the corpus index.

    query               — free-text query string
    section_id          — filter to a specific section (e.g. "3.4")
    content_class       — filter by content class (e.g. "METHODOLOGY_DEPENDENT")
    k                  — number of results to return (max 50)
    index              — optional index instance (default: global singleton)
    """
    if index is None:
        index = get_retrieval_index()

    cleaned = _clean_query(query)
    if not cleaned:
        return []

    if not index.is_built():
        _warn_no_index_once()
        return []

    k = min(k, MAX_K)
    terms = cleaned.split()

    raw = index.search(cleaned, section_id=section_id, content_class=content_class, k=k)

    results: list[RetrievalResult] = []
    for hit in raw:
        results.append(
            RetrievalResult(
                section_id=hit["section_id"],
                sub_section_id=hit.get("sub_section_id") or "",
                document_name=hit["document_name"],
                canonical_heading=hit["canonical_heading"],
                text=_highlight(hit["text"], terms),
                content_class=hit.get("content_class") or "",
                review_sensitivity=hit.get("review_sensitivity") or "",
                score=hit.get("score", 0.0),
                matched_terms=terms,
            )
        )
    return results


def get_examples_for_section(
    section_id: str,
    sub_section_id: str | None = None,
    k: int = DEFAULT_K,
    index: RetrievalIndex | None = None,
) -> list[RetrievalResult]:
    """Get non-ranked example texts for a specific section/sub-section."""
    if index is None:
        index = get_retrieval_index()

    k = min(k, MAX_K)

    if not index.is_built():
        _warn_no_index_once()
        return []

    if sub_section_id:
        raw = index.get_section_examples(section_id, sub_section_id=sub_section_id, k=k)
    else:
        raw = index.get_section_examples(section_id, k=k)

    return [
        RetrievalResult(
            section_id=r["section_id"],
            sub_section_id=r.get("sub_section_id") or "",
            document_name=r["document_name"],
            canonical_heading=r["canonical_heading"],
            text=r["text"],
            content_class=r.get("content_class") or "",
            review_sensitivity=r.get("review_sensitivity") or "",
            score=0.0,
            matched_terms=[],
        )
        for r in raw
    ]


def get_section_heading_examples(
    heading: str,
    k: int = 3,
    index: RetrievalIndex | None = None,
) -> list[RetrievalResult]:
    """Find corpus examples by near-exact heading match."""
    if index is None:
        index = get_retrieval_index()

    if not index.is_built():
        _warn_no_index_once()
        return []

    raw = index.search_by_heading(heading, k=k)
    return [
        RetrievalResult(
            section_id=r["section_id"],
            sub_section_id=r.get("sub_section_id") or "",
            document_name=r["document_name"],
            canonical_heading=r["canonical_heading"],
            text=r["text"],
            content_class=r.get("content_class") or "",
            review_sensitivity=r.get("review_sensitivity") or "",
            score=0.0,
            matched_terms=[],
        )
        for r in raw
    ]
