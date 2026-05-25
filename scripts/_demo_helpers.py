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
