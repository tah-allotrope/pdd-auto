"""Parser: maps normalized corpus documents to the canonical PDD section schema.

Reads `.norm.json` files from the normalized corpus directory and produces
a per-document, per-section coverage report indicating how well each canonical
section is represented in each source document.
"""

from __future__ import annotations

import json
import re
import structlog
from pathlib import Path
from typing import Any

import yaml

logger = structlog.get_logger()


def _load_schema(schema_path: Path) -> dict[str, Any]:
    with open(schema_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    sections = {}
    for sec in raw["sections"]:
        sid = sec["section_id"]
        sections[sid] = {
            "canonical_heading": sec["canonical_heading"],
            "section_type": sec.get("section_type", ""),
            "content_class": sec.get("content_class", ""),
            "review_sensitivity": sec.get("review_sensitivity", ""),
            "boilerplate_level": sec.get("boilerplate_level", ""),
            "sub_sections": {s["sub_section_id"]: s for s in sec.get("sub_sections", [])},
            "aliases": sec.get("aliases", []),
        }
    return sections


def _build_alias_index(sections: dict[str, Any]) -> dict[str, tuple[str, str]]:
    """Map every observed heading variant -> (section_id, sub_section_id)."""
    index: dict[str, tuple[str, str]] = {}
    for sid, sinfo in sections.items():
        index[sinfo["canonical_heading"].upper()] = (sid, "")
        for alias in sinfo.get("aliases", []):
            index[alias.upper()] = (sid, "")
        for ssid, ssinfo in sinfo["sub_sections"].items():
            key = ssinfo["heading"].upper()
            index[key] = (sid, ssid)
            for alias in ssinfo.get("aliases", []):
                index[alias.upper()] = (sid, ssid)
    return index


def _normalize_heading(text: str) -> str:
    """Strip whitespace and normalize to uppercase for comparison."""
    return text.strip().upper()


def _best_match(heading: str, alias_index: dict[str, tuple[str, str]]) -> tuple[str, str] | None:
    """Find best section match for a heading string.

    Tries exact match first, then partial match (heading contained in alias).
    """
    norm = _normalize_heading(heading)
    if norm in alias_index:
        return alias_index[norm]
    for alias, (sid, ssid) in alias_index.items():
        if norm in alias or alias in norm:
            return (sid, ssid)
    return None


def parse_document(
    norm_json_path: Path,
    schema_path: Path | None = None,
) -> dict[str, Any]:
    """Parse a single `.norm.json` file and return section coverage.

    Returns a dict with keys:
      - document_name: str
      - file_path: str
      - total_headings: int
      - sections_mapped: list of matched section info
      - sections_unmapped: list of unmapped headings
      - coverage_summary: dict mapping section_id -> coverage_level
    """
    if schema_path is None:
        schema_path = (
            Path(__file__).parent.parent.parent.parent / "schemas" / "pdd_section_schema.yaml"
        )
    schema_path = Path(schema_path)

    sections = _load_schema(schema_path)
    alias_index = _build_alias_index(sections)

    with open(norm_json_path, encoding="utf-8") as f:
        doc = json.load(f)

    doc_name = norm_json_path.stem
    headings: list[dict[str, Any]] = doc.get("headings", [])
    text_blocks: list[dict[str, Any]] = doc.get("text_blocks", [])
    pages: list[dict[str, Any]] = doc.get("pages", [])

    sections_mapped: list[dict[str, Any]] = []
    sections_unmapped: list[dict[str, Any]] = []

    def _strip_page_number(text: str) -> str:
        return re.sub(r"\s+\d+$", "", text.strip())

    page_texts: dict[int, str] = {p["page"]: p.get("text", "") for p in pages}
    max_page = max(page_texts.keys()) if page_texts else 1

    def _is_toc_page(text: str) -> bool:
        if not text:
            return False
        upper = text[:100].upper()
        if "CONTENTS" in upper or "TABLE OF CONTENTS" in upper:
            return True
        dotted_lines = re.findall(r"\d+\.\d+\s+[A-Z]", text)
        return len(dotted_lines) >= 8

    def _find_content_page(start_page: int, canonical_heading: str) -> str:
        target_upper = canonical_heading.upper()
        for pg in range(start_page, max_page + 1):
            pg_text = page_texts.get(pg, "")
            if not pg_text.strip() or _is_toc_page(pg_text):
                continue
            if target_upper in pg_text.upper():
                return pg_text.strip()[:500]
        for pg in range(start_page, max_page + 1):
            pg_text = page_texts.get(pg, "")
            if pg_text.strip() and not _is_toc_page(pg_text):
                return pg_text.strip()[:500]
        return ""

    for idx, h in enumerate(headings):
        match = _best_match(h["text"], alias_index)
        h_page: int = h.get("page", 1)
        canonical = (
            (
                sections[match[0]]["sub_sections"][match[1]]["heading"]
                if match and match[1] and match[1] in sections[match[0]]["sub_sections"]
                else sections[match[0]]["canonical_heading"]
            )
            if match
            else ""
        )
        text_preview = _find_content_page(h_page, canonical)
        if match:
            sid, ssid = match
            sections_mapped.append(
                {
                    "heading_text": h["text"],
                    "canonical_section_id": sid,
                    "canonical_sub_section_id": ssid or None,
                    "canonical_heading": (
                        sections[sid]["sub_sections"][ssid]["heading"]
                        if ssid and ssid in sections[sid]["sub_sections"]
                        else sections[sid]["canonical_heading"]
                    ),
                    "level": h.get("level", 0),
                    "text_preview": text_preview,
                }
            )
        else:
            sections_unmapped.append(
                {
                    "heading_text": h["text"],
                    "level": h.get("level", 0),
                    "text_preview": text_preview,
                }
            )

    coverage: dict[str, str] = {}
    for sid in sections:
        sub_count = len(sections[sid]["sub_sections"])
        if sub_count == 0:
            matched = any(m["canonical_section_id"] == sid for m in sections_mapped)
            coverage[sid] = "FULL" if matched else "MISSING"
        else:
            matched_subs = sum(
                1
                for m in sections_mapped
                if m["canonical_section_id"] == sid and m["canonical_sub_section_id"]
            )
            total_subs = sub_count
            if matched_subs == total_subs:
                coverage[sid] = "FULL"
            elif matched_subs > 0:
                coverage[sid] = "PARTIAL"
            else:
                coverage[sid] = "MISSING"

    return {
        "document_name": doc_name,
        "file_path": str(norm_json_path),
        "total_headings": len(headings),
        "sections_mapped": sections_mapped,
        "sections_unmapped": sections_unmapped,
        "coverage": coverage,
    }


def parse_corpus(
    normalized_dir: Path | None = None,
    schema_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Parse all `.norm.json` files in the normalized corpus directory."""
    if normalized_dir is None:
        normalized_dir = (
            Path(__file__).parent.parent.parent.parent / "data" / "corpus" / "normalized"
        )
    normalized_dir = Path(normalized_dir)

    results: list[dict[str, Any]] = []
    for p in sorted(normalized_dir.glob("*.norm.json")):
        try:
            result = parse_document(p, schema_path)
            results.append(result)
        except Exception as exc:
            logger.warning("parse_document_failed", path=str(p), error=str(exc))
            results.append(
                {
                    "document_name": p.stem,
                    "file_path": str(p),
                    "error": str(exc),
                }
            )
    return results


def build_corpus_section_index(
    parsed_corpus: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build a reverse index: canonical section_id -> {document -> coverage_entry}."""
    index: dict[str, dict[str, Any]] = {}
    for doc_result in parsed_corpus:
        if "error" in doc_result:
            continue
        for sid, level in doc_result.get("coverage", {}).items():
            if sid not in index:
                index[sid] = {}
            index[sid][doc_result["document_name"]] = level
    return index


def get_section_texts(
    parsed_corpus: list[dict[str, Any]],
    section_id: str,
    sub_section_id: str | None = None,
    content_class: str | None = None,
    max_examples: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve text previews for a given section across corpus documents.

    Useful for retrieving examples before drafting a new section.
    """
    examples: list[dict[str, Any]] = []
    for doc_result in parsed_corpus:
        if "error" in doc_result:
            continue
        for entry in doc_result.get("sections_mapped", []):
            if entry["canonical_section_id"] != section_id:
                continue
            if sub_section_id and entry["canonical_sub_section_id"] != sub_section_id:
                continue
            examples.append(
                {
                    "document_name": doc_result["document_name"],
                    "heading_text": entry["heading_text"],
                    "canonical_heading": entry["canonical_heading"],
                    "text_preview": entry.get("text_preview", ""),
                }
            )
            if len(examples) >= max_examples:
                break
        if len(examples) >= max_examples:
            break
    return examples
