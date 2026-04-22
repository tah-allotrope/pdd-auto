"""Thin wrapper around gws CLI for uploading PDD artifacts to Google Drive.

Uses the gws binary at the npm global path. Uploaded files are placed
in the VERRA project folder by default.
"""

from __future__ import annotations

import subprocess
import structlog
from pathlib import Path

logger = structlog.get_logger()

_GWS_PATH = Path.home() / "AppData/Roaming/npm/gws.cmd"
_DEFAULT_FOLDER_ID = "1pp23yRZ8qtopw1BPXrzVewXsmmWplCse"


def upload_file(
    local_path: Path,
    drive_folder_id: str | None = None,
    drive_name: str | None = None,
) -> dict:
    """Upload a file to Google Drive using gws.

    Args:
        local_path: Path to the local file to upload.
        drive_folder_id: Target folder ID in Google Drive (defaults to VERRA folder).
        drive_name: Optional display name in Drive (defaults to filename).

    Returns:
        dict with keys: success (bool), drive_url (str | None), file_id (str | None)
    """
    if not local_path.exists():
        logger.error("upload_file_not_found", path=str(local_path))
        return {"success": False, "drive_url": None, "file_id": None, "error": "File not found"}

    folder_id = drive_folder_id or _DEFAULT_FOLDER_ID
    name = drive_name or local_path.name

    cmd = [
        str(_GWS_PATH),
        "drive",
        "files",
        "create",
        "--folder-id",
        folder_id,
        "--name",
        name,
        str(local_path.resolve()),
    ]

    logger.info("gws_upload_start", file=local_path.name, folder=folder_id)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            logger.error(
                "gws_upload_failed",
                rc=result.returncode,
                stderr=stderr,
                stdout=stdout,
            )
            return {
                "success": False,
                "drive_url": None,
                "file_id": None,
                "error": stderr or stdout or f"Exit code {result.returncode}",
            }

        drive_url = _parse_drive_url(stdout) or _build_drive_url_from_name(name, folder_id)
        file_id = _parse_file_id(stdout) or None

        logger.info("gws_upload_success", file=local_path.name, drive_url=drive_url)
        return {"success": True, "drive_url": drive_url, "file_id": file_id, "error": None}

    except subprocess.TimeoutExpired:
        logger.error("gws_upload_timeout", file=local_path.name)
        return {
            "success": False,
            "drive_url": None,
            "file_id": None,
            "error": "Upload timed out (>120s)",
        }
    except Exception as exc:
        logger.error("gws_upload_error", file=local_path.name, error=str(exc))
        return {"success": False, "drive_url": None, "file_id": None, "error": str(exc)}


def upload_docx_run(
    run_id: str,
    runs_dir: Path | None = None,
    drive_folder_id: str | None = None,
) -> dict:
    """Convenience wrapper to upload a .docx file for a given run_id.

    Args:
        run_id: The run identifier.
        runs_dir: Directory containing run artifacts (defaults to data/runs).
        drive_folder_id: Target Drive folder ID.

    Returns:
        dict with upload result (same shape as upload_file).
    """
    if runs_dir is None:
        runs_dir = Path(__file__).parent.parent.parent.parent / "data" / "runs"
    runs_dir = Path(runs_dir)

    docx_path = runs_dir / f"{run_id}.docx"
    return upload_file(docx_path, drive_folder_id=drive_folder_id)


def _parse_drive_url(stdout: str) -> str | None:
    import re

    url_match = re.search(r"https://drive\.google\.com/file/d/[\w-]+", stdout)
    return url_match.group(0) if url_match else None


def _parse_file_id(stdout: str) -> str | None:
    import re

    id_match = re.search(r"([\w-]{20,})", stdout)
    return id_match.group(1) if id_match else None


def _build_drive_url_from_name(name: str, folder_id: str) -> str:
    return f"https://drive.google.com/drive/folders/{folder_id}"
