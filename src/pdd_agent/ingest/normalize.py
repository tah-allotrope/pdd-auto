"""Normalize raw corpus files (PDF / DOCX) into plain text with heading metadata."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

import structlog

from pdd_agent.ingest.drive import is_blob, is_workspace_native

log = structlog.get_logger(__name__)

NORM_DIR = Path("data/corpus/normalized")
HEADING_RE = re.compile(r"^(#{1,6}\s+|[A-Z0-9][\.\d]+[\s])")


def normalize_corpus(manifest_path: str, dry_run: bool = False) -> None:
    """Read manifest, normalize each cache file, and write per-file JSON normalization records.

    Args:
        manifest_path:  Path to the JSONL manifest.
        dry_run:  If True, log what would be normalized without writing.
    """
    manifest = Path(manifest_path)
    if not manifest.exists():
        log.error("manifest_missing", path=str(manifest))
        raise FileNotFoundError(manifest_path)

    if not dry_run:
        NORM_DIR.mkdir(parents=True, exist_ok=True)

    processed = 0
    skipped = 0
    failed = 0
    entries: list[dict[str, Any]] = []

    with open(manifest, encoding="utf-8") as fh:
        for line in fh:
            entry = json.loads(line.strip())
            raw_path = Path(entry["local_raw_path"])
            mime_type = entry["mime_type"]
            norm_path = NORM_DIR / (raw_path.stem + ".norm.json")

            entry["local_norm_path"] = str(norm_path)

            if not is_blob(mime_type):
                log.debug("skip_non_blob", file_id=entry["id"], mime_type=mime_type)
                skipped += 1
                entries.append(entry)
                continue

            if not raw_path.exists():
                log.warning("raw_file_missing_skip", file_id=entry["id"])
                skipped += 1
                failed += 1
                entries.append(entry)
                continue

            try:
                result = _extract_text(raw_path, mime_type, dry_run=dry_run)
                if not dry_run:
                    safe_result = _sanitize_for_json(result)
                    with open(norm_path, "w", encoding="utf-8") as nf:
                        json.dump(safe_result, nf, ensure_ascii=False, indent=2)
                entry["parseable"] = result["parseable"]
                entry["word_count"] = result["word_count"]
                entry["heading_count"] = result["heading_count"]
                entry["norm_uuid"] = str(uuid.uuid4())
                log.info(
                    "normalized",
                    file_id=entry["id"],
                    words=result["word_count"],
                    headings=result["heading_count"],
                )
                processed += 1
            except Exception as exc:
                log.error("normalize_failed", file_id=entry["id"], error=str(exc))
                entry["parseable"] = False
                entry["word_count"] = 0
                entry["heading_count"] = 0
                entry["norm_uuid"] = str(uuid.uuid4())
                failed += 1

            entries.append(entry)

    # Re-write manifest with normalized metadata
    if not dry_run:
        with open(manifest_path, "w", encoding="utf-8") as fh:
            for e in entries:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
        log.info("normalization_done", processed=processed, skipped=skipped, failed=failed)

    log.info("normalize_complete", processed=processed, skipped=skipped, failed=failed)


def _sanitize_for_json(d: dict[str, Any]) -> dict[str, Any]:
    """Replace surrogate characters that can't be encoded in UTF-8 JSON."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, str):
            try:
                v.encode("utf-8", errors="surrogatepass").decode("utf-8")
                out[k] = v
            except (UnicodeDecodeError, UnicodeEncodeError):
                out[k] = v.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")
        elif isinstance(v, list):
            out[k] = [_sanitize_for_json(i) if isinstance(i, dict) else i for i in v]
        elif isinstance(v, dict):
            out[k] = _sanitize_for_json(v)
        else:
            out[k] = v
    return out


def _extract_text(path: Path, mime_type: str, dry_run: bool = False) -> dict[str, Any]:
    """Extract plain text from a PDF or DOCX file."""
    result: dict[str, Any] = {
        "file": str(path),
        "mime_type": mime_type,
        "parseable": False,
        "word_count": 0,
        "heading_count": 0,
        "pages": [],
        "text": "",
    }

    if mime_type == "application/pdf":
        inner = _extract_pdf(path, dry_run=dry_run)
        if dry_run:
            inner["parseable"] = True
        result.update(inner)
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        inner = _extract_docx(path, dry_run=dry_run)
        if dry_run:
            inner["parseable"] = True
        result.update(inner)
    else:
        result["error"] = f"Unsupported MIME type: {mime_type}"

    text = result.get("text", "")
    result["word_count"] = len(text.split()) if text else 0
    headings = [ln.strip() for ln in text.splitlines() if HEADING_RE.match(ln.strip())]
    result["heading_count"] = len(headings)
    if dry_run:
        result["parseable"] = True
    else:
        result["parseable"] = result.get("parseable", False) and result["word_count"] > 100

    return result


def _build_headings_and_blocks(
    lines: list[str],
    page_starts: dict[int, int] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse lines into headings and text blocks for section_parser compatibility.

    headings: list of {text, level, page} for lines matching HEADING_RE
    text_blocks: list of {heading, text} segments between headings
    page_starts: optional map from line index -> 1-based page number
    """
    headings: list[dict[str, Any]] = []
    text_blocks: list[dict[str, Any]] = []

    current_heading = ""
    current_text_lines: list[str] = []

    def _is_heading(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if stripped.startswith("#"):
            return True
        if HEADING_RE.match(stripped):
            return True
        return False

    for idx, line in enumerate(lines):
        if _is_heading(line):
            if current_heading or current_text_lines:
                text_blocks.append(
                    {
                        "heading": current_heading,
                        "text": "\n".join(current_text_lines).strip(),
                    }
                )
            level = 1
            if line.strip().startswith("#"):
                level = len(line.split()[0]) if line.split() else 1
            elif line[0].isdigit():
                level = 1
            heading_entry: dict[str, Any] = {"text": line.strip(), "level": level}
            if page_starts is not None:
                pg = page_starts.get(idx, 1)
                heading_entry["page"] = pg
            headings.append(heading_entry)
            current_heading = line.strip()
            current_text_lines = []
        else:
            current_text_lines.append(line)

    if current_heading or current_text_lines:
        text_blocks.append(
            {
                "heading": current_heading,
                "text": "\n".join(current_text_lines).strip(),
            }
        )

    return headings, text_blocks


def _extract_pdf(path: Path, dry_run: bool = False) -> dict[str, Any]:
    """Extract text from a PDF using pypdf."""
    out: dict[str, Any] = {
        "parseable": False,
        "pages": [],
        "text": "",
        "headings": [],
        "text_blocks": [],
    }

    if dry_run:
        out["parseable"] = True
        out["text"] = "[dry-run PDF content placeholder]"
        out["headings"] = []
        out["text_blocks"] = []
        return out

    try:
        from pypdf import PdfReader
    except ImportError:
        out["error"] = "pypdf not installed"
        return out

    try:
        reader = PdfReader(str(path))
        pages: list[dict[str, Any]] = []
        all_lines: list[str] = []
        page_starts: dict[int, int] = {}

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            lines = text.splitlines()
            page_starts[len(all_lines)] = i + 1
            all_lines.extend(lines)
            pages.append({"page": i + 1, "chars": len(text), "text": text})

        full_text = "\n".join(all_lines)
        headings, text_blocks = _build_headings_and_blocks(all_lines, page_starts)
        out["pages"] = pages
        out["text"] = full_text
        out["headings"] = headings
        out["text_blocks"] = text_blocks
        out["parseable"] = True
        out["page_count"] = len(reader.pages)
    except Exception as exc:
        out["error"] = str(exc)

    return out


def _extract_docx(path: Path, dry_run: bool = False) -> dict[str, Any]:
    """Extract text from a DOCX using python-docx."""
    out: dict[str, Any] = {
        "parseable": False,
        "pages": [],
        "text": "",
        "headings": [],
        "text_blocks": [],
    }

    if dry_run:
        out["parseable"] = True
        out["text"] = "[dry-run DOCX content placeholder]"
        out["headings"] = []
        out["text_blocks"] = []
        return out

    try:
        from docx import Document
    except ImportError:
        out["error"] = "python-docx not installed"
        return out

    try:
        doc = Document(str(path))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        full_text = "\n".join(paragraphs)
        headings, text_blocks = _build_headings_and_blocks(paragraphs)
        out["text"] = full_text
        out["headings"] = headings
        out["text_blocks"] = text_blocks
        out["parseable"] = True
        out["page_count"] = 1
        out["pages"] = [{"page": 1, "chars": len(full_text), "text": full_text}]
    except Exception as exc:
        out["error"] = str(exc)

    return out
