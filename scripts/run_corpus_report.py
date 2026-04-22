"""One-shot corpus readiness report generator.

Run after a successful `pdd-agent ingest` to produce a human-readable
markdown summary of the corpus state.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

MANIFEST_PATH = Path("data/corpus/manifest.jsonl")
BUCKET_CONFIG_PATH = Path("configs/corpus_buckets/verra-wte-initial.yaml")
REPORT_PATH = Path("reports/corpus-readiness.md")


def main() -> int:
    if not MANIFEST_PATH.exists():
        print(f"ERROR: Manifest not found at {MANIFEST_PATH}", file=sys.stderr)
        print("Run:  pdd-agent ingest  first.", file=sys.stderr)
        return 1

    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        entries = [json.loads(line.strip()) for line in fh if line.strip()]

    config = {}
    if BUCKET_CONFIG_PATH.exists():
        with open(BUCKET_CONFIG_PATH, encoding="utf-8") as fh:
            config = yaml.safe_load(fh)

    report = _build_report(entries, config)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Report written to: {REPORT_PATH}")
    print(report)
    return 0


def _build_report(entries: list[dict], config: dict) -> str:
    total = len(entries)
    parseable = sum(1 for e in entries if e.get("parseable", False))
    in_bucket = sum(1 for e in entries if e.get("bucket") == "IN_BUCKET")
    out_bucket = sum(1 for e in entries if e.get("bucket") == "OUT_OF_BUCKET")
    needs_review = sum(1 for e in entries if e.get("bucket") == "NEEDS_REVIEW")

    mime_counts: dict[str, int] = defaultdict(int)
    for e in entries:
        mime_counts[e.get("mime_type", "unknown")] += 1

    total_words = sum(e.get("word_count", 0) for e in entries)
    total_pages = sum(len(e.get("pages", [])) for e in entries)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# Corpus Readiness Report — VERRA WTE Bucket",
        f"**Generated:** {now}",
        f"**Source folder:** `1pp23yRZ8qtopw1BPXrzVewXsmmWplCse` (VERRA)",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"| --- | --- |",
        f"| Total files inventoried | {total} |",
        f"| Parseable (PDF/DOCX) | {parseable} |",
        f"| In initial bucket | {in_bucket} |",
        f"| Out of bucket | {out_bucket} |",
        f"| Needs manual review | {needs_review} |",
        f"| Total words (normalized) | {total_words:,} |",
        f"| Total pages extracted | {total_pages} |",
        "",
        "## MIME Type Distribution",
        "",
    ]

    for mime, count in sorted(mime_counts.items()):
        lines.append(f"- `{mime}`: {count}")

    lines += [
        "",
        "## Per-File Detail",
        "",
        f"| File | MIME | Bucket | Words | Headings | Parseable |",
        f"| --- | --- | --- | ---: | ---: | ---: |",
    ]

    for e in sorted(entries, key=lambda x: x.get("name", "")):
        name = e.get("name", "unknown")
        mime = e.get("mime_type", "unknown")
        mime_short = (
            mime.split(".")[-1].replace("vnd.", "").replace("openxmlformats-officedocument.", "")
        )
        bucket = e.get("bucket") or "PENDING"
        words = e.get("word_count", 0)
        headings = e.get("heading_count", 0)
        parseable = "YES" if e.get("parseable") else "NO"
        bucket_reason = e.get("bucket_reason", "")

        bucket_display = f"`{bucket}`" + (
            f" — {bucket_reason}" if bucket == "OUT_OF_BUCKET" else ""
        )
        lines.append(
            f"| {name} | {mime_short} | {bucket_display} | {words:,} | {headings} | {parseable} |"
        )

    lines += [
        "",
        "## Bucket Configuration",
        "",
        f"- **Config file:** `{BUCKET_CONFIG_PATH}`",
        f"- **Bucket name:** `{config.get('bucket_name', 'N/A')}`",
        f"- **Description:** {config.get('description', 'N/A')}",
        "",
        "## Next Steps",
        "",
        "1. **Review NEEDS_REVIEW files** — manually inspect files flagged NEEDS_REVIEW and either move them out of the Drive folder or lower the inclusion threshold in the bucket config.",
        "2. **Confirm reference materials** — download official Verra template and methodology documents into `data/reference/verra/` and `data/reference/methodologies/`.",
        "3. **Validate parseability** — for any file flagged NOT parseable, check whether it is a scanned PDF requiring OCR.",
        "4. **Lock bucket before PHASE-02** — once the in-bucket set is stable, update `configs/corpus_buckets/verra-wte-initial.yaml` and commit the manifest.",
        "",
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
