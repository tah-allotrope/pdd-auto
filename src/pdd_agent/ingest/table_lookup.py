"""Helper for reading extracted tables out of a normalized corpus record."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import structlog

logger = structlog.get_logger(__name__)

_DEFAULT_NORM_DIR = Path("data/corpus/normalized")


def find_tables(
    document_stem: str,
    must_contain: Sequence[str],
    normalized_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Return every extracted table of *document_stem* whose text contains all *must_contain*.

    Each entry is ``{"page": int, "table_index": int, "rows": list[list[str]]}``.
    Returns ``[]`` when the document, file, or tables key is missing.
    """
    norm_dir = Path(normalized_dir) if normalized_dir is not None else _DEFAULT_NORM_DIR
    norm_path = norm_dir / f"{document_stem}.norm.json"
    if not norm_path.exists():
        return []
    try:
        data = json.loads(norm_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    tables = data.get("tables")
    if not isinstance(tables, list):
        return []
    needles = [s.lower() for s in must_contain]
    out: list[dict[str, Any]] = []
    for t in tables:
        rows = t.get("rows") if isinstance(t, dict) else None
        if not isinstance(rows, list):
            continue
        flat = " ".join(" ".join(str(c) for c in r) for r in rows if isinstance(r, list)).lower()
        if all(n in flat for n in needles):
            out.append(
                {"page": t.get("page", 0), "table_index": t.get("table_index", 0), "rows": rows}
            )
    return out


def table_rows_as_pairs(
    table: dict[str, Any], key_column: int = 0, value_column: int = 1
) -> list[tuple[str, str]]:
    """Return (key, value) pairs of stripped cell text for rows with both cells non-empty."""
    rows = table.get("rows", [])
    pairs: list[tuple[str, str]] = []
    for row in rows:
        if not isinstance(row, list):
            continue
        if len(row) <= max(key_column, value_column):
            continue
        key = str(row[key_column]).strip()
        value = str(row[value_column]).strip()
        if not key or not value:
            continue
        pairs.append((key, value))
    return pairs
