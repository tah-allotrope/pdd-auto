"""Bucket assignment for corpus documents.

Each document is evaluated against the current bucket configuration
and labelled as IN_BUCKET, OUT_OF_BUCKET, or NEEDS_REVIEW.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import structlog
import yaml

from pdd_agent.ingest.drive import is_blob

log = structlog.get_logger(__name__)

BUCKET_CONFIG_PATH = Path("configs/corpus_buckets/verra-wte-initial.yaml")


def load_bucket_config() -> dict[str, Any]:
    """Load and parse the active corpus bucket configuration."""
    if not BUCKET_CONFIG_PATH.exists():
        log.warning("bucket_config_missing", path=str(BUCKET_CONFIG_PATH))
        return {}
    with open(BUCKET_CONFIG_PATH, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    log.info("bucket_config_loaded", path=str(BUCKET_CONFIG_PATH))
    return cfg


def bucket_documents(manifest_path: str, config: dict[str, Any]) -> None:
    """Read the manifest, score each document against the active bucket config, and write bucket labels.

    Args:
        manifest_path:  Path to the JSONL manifest.
        config:  Parsed bucket configuration dict.
    """
    manifest = Path(manifest_path)
    if not manifest.exists():
        log.error("manifest_missing", path=str(manifest))
        raise FileNotFoundError(manifest_path)

    cfg = config or {}
    rules = cfg.get("bucket_rules", {})
    inclusion = rules.get("include", {})
    exclusion = rules.get("exclude", {})

    updated = 0
    in_bucket = 0
    out_of_bucket = 0

    # Collect all entries so we can re-write atomically
    entries: list[dict[str, Any]] = []
    with open(manifest, encoding="utf-8") as fh:
        for line in fh:
            entries.append(json.loads(line.strip()))

    for entry in entries:
        file_id = entry["id"]
        name = entry["name"]
        mime_type = entry["mime_type"]

        bucket_label, reason = _score_entry(entry, inclusion, exclusion)

        entry["bucket"] = bucket_label
        entry["bucket_reason"] = reason

        if bucket_label == "IN_BUCKET":
            in_bucket += 1
        else:
            out_of_bucket += 1

        log.info(
            "bucket_assigned",
            file_id=file_id,
            name=name,
            bucket=bucket_label,
            reason=reason,
        )
        updated += 1

    # Rewrite manifest with bucket labels
    with open(manifest_path, "w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    log.info(
        "bucket_complete",
        total=updated,
        in_bucket=in_bucket,
        out_of_bucket=out_of_bucket,
    )


def _score_entry(
    entry: dict[str, Any],
    inclusion: dict[str, Any],
    exclusion: dict[str, Any],
) -> tuple[str, str]:
    """Return (bucket_label, reason) for a single manifest entry."""
    name = entry["name"].lower()
    mime_type = entry["mime_type"]
    word_count = entry.get("word_count", 0)
    heading_count = entry.get("heading_count", 0)

    # Exclusion checks first
    for pattern in exclusion.get("name_patterns", []):
        if re.search(pattern, name, re.IGNORECASE):
            return "OUT_OF_BUCKET", f"name matches exclusion pattern: {pattern}"

    for mime in exclusion.get("mime_types", []):
        if mime_type == mime:
            return "OUT_OF_BUCKET", f"MIME type excluded: {mime_type}"

    # File-type gate: must be a blob we can actually parse
    if not is_blob(mime_type):
        return "OUT_OF_BUCKET", f"non-blob MIME type: {mime_type}"

    # Parseability gate
    if word_count < 100:
        return "NEEDS_REVIEW", f"too few words ({word_count}) — possible scan/OCR needed"

    # Inclusion checks
    include_name_patterns = inclusion.get("name_patterns", [])
    exclude_name_patterns = exclusion.get("name_patterns", [])

    if include_name_patterns:
        matched = any(re.search(p, name, re.IGNORECASE) for p in include_name_patterns)
        if not matched:
            return "OUT_OF_BUCKET", "name does not match any inclusion pattern"

    # WTE-specific keyword scoring
    wte_keywords = [
        "waste",
        "wte",
        "energy",
        "incineration",
        "renewable",
        "landfill",
        "municipal solid waste",
        "msw",
        "anaerobic",
        "biogas",
        "rdf",
        "refuse derived",
        "soc son",
        "guangxi",
        "ninh",
        "linfen",
        "yingoku",
        "bergama",
        "inegol",
        "mahindra",
        "tamil nadu",
    ]
    name_hits = sum(1 for kw in wte_keywords if kw in name)
    heading_ratio = heading_count / max(word_count, 1)

    # Quality heuristics
    if word_count < 500:
        return "NEEDS_REVIEW", f"low word count ({word_count}) — may be fragment or cover page"

    if name_hits >= 1 or "project" in name:
        return "IN_BUCKET", f"passed inclusion (keyword hits={name_hits})"

    return (
        "NEEDS_REVIEW",
        f"uncertain classification — keyword hits={name_hits}, manual review recommended",
    )


def write_default_bucket_config() -> None:
    """Write the default WTE-focused bucket config if it doesn't exist."""
    BUCKET_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if BUCKET_CONFIG_PATH.exists():
        log.info("bucket_config_already_exists", path=str(BUCKET_CONFIG_PATH))
        return

    config = {
        "bucket_name": "verra-wte-initial",
        "description": (
            "Initial homogeneous bucket: Verra-style waste-to-energy PDDs "
            "from the shared VERRA Drive folder, covering MSW, WTE, AD, RDF, "
            "and landfill-diversion project types. Excludes non-WTE and "
            "non-Verra standards."
        ),
        "version": "0.1.0",
        "bucket_rules": {
            "include": {
                "name_patterns": [
                    r"vcs_.*project.*description",
                    r"vcs_.*waste.*power",
                    r"vcs_.*msw",
                    r"vcs_.*renewable.*energy",
                    r"vcs_.*soc.*son",
                    r"vcs_.*guangxi",
                    r"vcs_.*linfen",
                    r"vcs_.*yingoku",
                    r"vcs_.*bergama",
                    r"vcs_.*inegol",
                    r"vcs_.*mahindra",
                    r"vcs_.*tamil",
                    r"vcs_.*odemis",
                    r"vcs_.*yanzhou",
                    r"vcs_.*shunping",
                    r"vcs_.*lizuhou",
                ],
                "mime_types": [
                    "application/pdf",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/msword",
                ],
                "min_word_count": 500,
                "methodology_family": ["ACM0022", "AMS-III.AJ", "ACM0003", "VMR0044"],
                "registry": ["VCS", "Verra"],
                "geography": ["Vietnam", "China", "India", "Turkey", "Southeast Asia"],
            },
            "exclude": {
                "name_patterns": [
                    r"draft.*internal",
                    r"note|todo|meeting",
                    r"methodology.*pdf",
                    r"template.*docx",
                ],
                "mime_types": [
                    "application/vnd.google-apps.folder",
                    "application/vnd.google-apps.document",
                    "application/vnd.google-apps.spreadsheet",
                    "text/plain",
                    "text/html",
                ],
            },
        },
        "notes": (
            "The include patterns intentionally list known WTE project names "
            "from the VERRA folder to bootstrap a narrow first bucket. "
            "Expand patterns after the first demo run."
        ),
    }

    with open(BUCKET_CONFIG_PATH, "w", encoding="utf-8") as fh:
        yaml.dump(config, fh, allow_unicode=True, sort_keys=False)

    log.info("bucket_config_written", path=str(BUCKET_CONFIG_PATH))
