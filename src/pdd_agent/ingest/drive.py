"""Drive ingestion layer – thin wrappers around `gws` CLI calls.

All actual Drive I/O goes through subprocess calls to `gws`.
No Google SDK / OAuth is required at the application layer.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)

GWS = str(Path.home() / "AppData" / "Roaming" / "npm" / "gws.cmd")
if not Path(GWS).exists():
    GWS = "gws"  # fallback to PATH lookup
VERRA_FOLDER_ID = "1pp23yRZ8qtopw1BPXrzVewXsmmWplCse"

GWS_ERROR_MESSAGE = (
    "gws CLI not found. Install it with 'npm install -g @googleworkspace/cli && gws auth setup'. "
    "Note: gws is only required for corpus ingestion and Drive upload — "
    "demo workflows (scripts/run_demo.py, scripts/run_inegol_demo.py) do not need it."
)


def _check_gws_available() -> None:
    """Raise a helpful RuntimeError if gws is not installed."""
    resolved = shutil.which(GWS)
    if resolved is None:
        raise RuntimeError(GWS_ERROR_MESSAGE)


def _run(args: list[str], timeout: int = 60) -> str:
    """Execute a gws command and return stdout as text."""
    _check_gws_available()
    log.debug("gws_call", args=args)
    result = subprocess.run(
        [GWS] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        log.error("gws_failed", returncode=result.returncode, stderr=result.stderr)
        raise RuntimeError(f"gws failed: {result.stderr.strip()}")
    return result.stdout


def list_folder(folder_id: str, page_size: int = 100) -> list[dict[str, Any]]:
    """Return file metadata dicts from a Drive folder."""
    output = _run(
        [
            "drive",
            "files",
            "list",
            "--params",
            json.dumps(
                {
                    "q": f"'{folder_id}' in parents and trashed=false",
                    "pageSize": page_size,
                    "fields": "files(id,name,mimeType,modifiedTime,parents,size)",
                    "orderBy": "folder,name,modifiedTime desc",
                }
            ),
            "--format",
            "json",
        ]
    )
    data = json.loads(output)
    return data.get("files", [])


def get_file_metadata(file_id: str) -> dict[str, Any]:
    """Return metadata for a single Drive file."""
    output = _run(
        [
            "drive",
            "files",
            "get",
            "--params",
            json.dumps(
                {
                    "fileId": file_id,
                    "fields": "id,name,mimeType,modifiedTime,parents,size,webViewLink,driveId",
                }
            ),
            "--format",
            "json",
        ]
    )
    return json.loads(output)


def download_blob(file_id: str, output_path: Path, mime_type: str) -> Path:
    """Download a blob file (PDF, DOCX, etc.) via gws alt=media."""
    output = _run(
        [
            "drive",
            "files",
            "get",
            "--params",
            json.dumps({"fileId": file_id, "alt": "media"}),
            "--output",
            str(output_path),
        ]
    )
    return output_path


def export_workspace_native(file_id: str, output_path: Path, mime_type: str) -> Path:
    """Export a Google Docs/Sheets/Slides native file to a downloadable format.

    MIME type mapping:
      application/vnd.google-apps.document → application/pdf
      application/vnd.google-apps.spreadsheet → application/pdf
      application/vnd.google-apps.presentation → application/pdf
    """
    export_mime = {
        "application/vnd.google-apps.document": "application/pdf",
        "application/vnd.google-apps.spreadsheet": "application/pdf",
        "application/vnd.google-apps.presentation": "application/pdf",
    }.get(mime_type)

    if not export_mime:
        raise ValueError(f"No export format known for MIME type: {mime_type}")

    output = _run(
        [
            "drive",
            "files",
            "export",
            "--params",
            json.dumps({"fileId": file_id, "mimeType": export_mime}),
            "--output",
            str(output_path),
        ]
    )
    return output_path


def is_workspace_native(mime_type: str) -> bool:
    return mime_type.startswith("application/vnd.google-apps")


def is_blob(mime_type: str) -> bool:
    """Return True for downloadable blob types we can process directly."""
    return mime_type == "application/pdf" or mime_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }


def drive_inventory(
    folder_id: str, manifest_path: str, dry_run: bool = False
) -> list[dict[str, Any]]:
    """List all files in the Drive folder and write a manifest entry per file.

    Args:
        folder_id:  Google Drive folder ID.
        manifest_path:  Path to write the JSONL manifest.
        dry_run:  If True, list files but do not write anything.

    Returns:
        List of manifest entry dicts (one per file).
    """
    log.info("drive_inventory_start", folder_id=folder_id, dry_run=dry_run)
    files = list_folder(folder_id)
    log.info("drive_files_found", count=len(files))

    manifest_dir = Path(manifest_path).parent
    if not dry_run:
        manifest_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    for f in files:
        entry = _build_entry(f)
        entries.append(entry)

    if not dry_run:
        with open(manifest_path, "w", encoding="utf-8") as fh:
            for e in entries:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
        log.info("manifest_written", path=manifest_path, entries=len(entries))

    return entries


def _build_entry(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw Drive file dict into a manifest entry."""
    file_id = raw["id"]
    name = raw["name"]
    mime_type = raw["mimeType"]
    modified = raw.get("modifiedTime", datetime.now(timezone.utc).isoformat())
    parents = raw.get("parents", [])
    size_kb = int(raw.get("size", 0)) // 1024

    local_path = _local_path_for(name, mime_type)

    return {
        "id": file_id,
        "name": name,
        "mime_type": mime_type,
        "modified": modified,
        "parents": parents,
        "size_kb": size_kb,
        "local_raw_path": str(local_path),
        "local_norm_path": None,
        "bucket": None,
        "parseable": is_blob(mime_type),
        "needs_export": is_workspace_native(mime_type),
        "inventory_uuid": str(uuid.uuid4()),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }


def _local_path_for(name: str, mime_type: str) -> Path:
    """Derive a stable local cache path for a Drive file.

    Strips any existing extension from the Drive-provided filename
    so we never produce double extensions like 'foo.pdf.pdf'.
    """
    stem = Path(name).stem
    safe_stem = "".join(c if c.isalnum() or c in "._-" else "_" for c in stem)
    ext = {
        "application/pdf": ".pdf",
        "application/vnd.google-apps.document": ".pdf",
        "application/vnd.google-apps.spreadsheet": ".pdf",
        "application/vnd.google-apps.presentation": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/msword": ".doc",
    }.get(mime_type, ".bin")
    return Path("data/corpus/raw/verra") / (safe_stem + ext)
