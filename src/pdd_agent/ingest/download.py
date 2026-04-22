"""Download corpus files from Drive based on a manifest entry."""

from __future__ import annotations

import json
from pathlib import Path

import structlog

from pdd_agent.ingest.drive import (
    download_blob,
    export_workspace_native,
    is_blob,
    is_workspace_native,
)

log = structlog.get_logger(__name__)


def download_corpus(manifest_path: str, dry_run: bool = False) -> None:
    """Read manifest and download each file that is not yet on disk.

    Args:
        manifest_path:  Path to the JSONL manifest produced by drive_inventory.
        dry_run:  If True, log what would be downloaded without writing files.
    """
    manifest = Path(manifest_path)
    if not manifest.exists():
        log.error("manifest_missing", path=str(manifest))
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    raw_dir = Path("data/corpus/raw/verra")
    if not dry_run:
        raw_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    skipped = 0
    errors = 0

    with open(manifest, encoding="utf-8") as fh:
        for line in fh:
            entry = json.loads(line.strip())
            file_id = entry["id"]
            local_path_str = entry["local_raw_path"]
            local_path = Path(local_path_str)
            mime_type = entry["mime_type"]

            # Skip if already on disk (check existence + non-zero size)
            if local_path.exists() and local_path.stat().st_size > 0:
                log.debug("already_cached", file_id=file_id, path=local_path)
                skipped += 1
                continue

            try:
                if is_blob(mime_type):
                    if dry_run:
                        log.info("would_download_blob", file_id=file_id, path=local_path)
                    else:
                        download_blob(file_id, local_path, mime_type)
                        log.info("blob_downloaded", file_id=file_id, path=str(local_path))
                        downloaded += 1

                elif is_workspace_native(mime_type):
                    if dry_run:
                        log.info("would_export_workspace_native", file_id=file_id, path=local_path)
                    else:
                        export_workspace_native(file_id, local_path, mime_type)
                        log.info("workspace_native_exported", file_id=file_id, path=str(local_path))
                        downloaded += 1
                else:
                    log.warning("unknown_mime_type_skipping", file_id=file_id, mime_type=mime_type)
                    skipped += 1

            except Exception as exc:
                log.error("download_failed", file_id=file_id, error=str(exc))
                errors += 1

    log.info("download_complete", downloaded=downloaded, skipped=skipped, errors=errors)
