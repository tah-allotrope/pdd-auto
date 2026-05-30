"""Shared helpers for demo script output formatting."""

from __future__ import annotations

import shutil
from pathlib import Path


def print_demo_banner(
    docx_path: str,
    run_id: str,
    sections_count: int,
    runtime: float,
    review_flags: str = "0 critical, 0 high",
    stable_path: str | None = None,
) -> None:
    """Print a user-friendly summary banner after a demo run."""
    w = 50
    lines = [
        "+" + "-" * w + "+",
        "|" + "  PDD Agent Demo Complete".ljust(w) + "|",
        "+" + "=" * w + "+",
        "|" + f"  Sections: {sections_count} | Runtime: {runtime:.1f}s".ljust(w) + "|",
        "|" + f"  Review flags: {review_flags}".ljust(w) + "|",
        "|" + " ".ljust(w) + "|",
        "|" + "  Your DOCX is at:".ljust(w) + "|",
    ]
    if stable_path:
        lines.append("|" + f"  -> {stable_path}".ljust(w) + "|")
    lines.append("|" + " ".ljust(w) + "|")
    lines.append("|" + "  Also saved to:".ljust(w) + "|")
    lines.append("|" + f"    {docx_path}".ljust(w) + "|")
    lines.append("+" + "-" * w + "+")

    print()
    for line in lines:
        print(line)
    print()


def copy_to_output(src: Path, dest_name: str) -> Path:
    """Copy a DOCX to output/<dest_name>, creating the directory if needed."""
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / dest_name
    shutil.copy2(src, dest)
    return dest


def ensure_demo_index() -> None:
    """Auto-build the demo retrieval index for corpus-backed provenance.

    No-ops when the production corpus index already exists, when the demo index
    is already built, or when the bundled demo corpus is absent (graceful
    degradation — the demo still runs, just without provenance citations).
    """
    from pdd_agent.demo_setup import (
        DEMO_CORPUS_DIR,
        DEMO_INDEX_PATH,
        build_demo_index,
    )

    corpus_index = DEMO_INDEX_PATH.parent / "corpus.fts.db"
    if corpus_index.exists() or DEMO_INDEX_PATH.exists():
        return
    if not DEMO_CORPUS_DIR.exists():
        return

    print("Auto-building demo index for corpus provenance...")
    build_demo_index()
