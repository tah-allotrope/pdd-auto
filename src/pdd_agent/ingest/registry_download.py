"""Public-registry PDD downloader.

Downloads registered Verra PDD PDFs for a given methodology family from the
public registry at ``https://registry.verra.org``.

**API shape verified during implementation** (2026-07-12, via ``curl`` probing
of the SPA's minified JS bundle — no browser devtools were available):

- The registry search SPA (served at ``https://registry.verra.org/app/search/VCS``)
  is an Angular app ("APX Registry" platform). Its ``SearchService`` sets
  ``basePath = "/uiapi"`` and POSTs to ``{basePath}/asset/asset/search``, i.e.
  same-origin ``https://registry.verra.org/uiapi/asset/asset/search``.
- The endpoint is reachable and responsive: a malformed request (arbitrary
  JSON body, no OData query params) returns ``HTTP 406 Unsupported format``
  rather than hanging, confirming it is live and validates its input.
- The exact OData request-body/query-param shape the Angular ``HttpClient``
  sends (``$filter``, ``$top``, ``$skip``, methodology-code field name, etc.)
  could not be fully reconstructed from the minified bundle alone without
  browser devtools network inspection of a real search interaction.

Given that, this module makes a best-effort real search attempt using the
verified endpoint and a plausible OData-shaped payload, but is built to fail
*fast and cleanly* rather than hang or crash: any non-2xx response, timeout,
or connection error triggers the documented manual-download fallback mode
(RISK-05-01 / ASM-003 in ``plans/2026-07-12-pdd-reality-gap-plan.md``) —
this is treated as a first-class supported outcome, not an error condition.
In manual mode, a human downloads PDDs from
https://registry.verra.org/app/search/VCS into ``output_dir`` by hand;
``refresh_manifest()`` then picks them up.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

_SEARCH_URL = "https://registry.verra.org/uiapi/asset/asset/search"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_MIN_REQUEST_INTERVAL_SECONDS = 2.0
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2.0
_REQUEST_TIMEOUT_SECONDS = 15

_last_request_time: float = 0.0


def _throttle() -> None:
    """Enforce a minimum interval between outbound HTTP requests."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL_SECONDS:
        time.sleep(_MIN_REQUEST_INTERVAL_SECONDS - elapsed)
    _last_request_time = time.monotonic()


def _sanitize_filename(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip())
    return cleaned.strip("_")[:120] or "untitled"


def _search_projects(methodology_id: str, limit: int) -> list[dict[str, Any]]:
    """Query the registry search API for projects using the given methodology.

    Returns a list of project records, each expected to carry at least
    ``project_id``, ``title``, and a document/PDF URL. Raises
    ``urllib.error.URLError``, ``TimeoutError``, or ``OSError`` on any
    network failure — callers must catch and fall back to manual mode.
    """
    payload = json.dumps(
        {
            "$filter": f"methodology eq '{methodology_id}' and program eq 'VCS'",
            "$top": limit,
            "$skip": 0,
        }
    ).encode("utf-8")

    _throttle()
    last_error: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            request = urllib.request.Request(
                _SEARCH_URL,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": _USER_AGENT,
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
                if response.status >= 400:
                    raise urllib.error.HTTPError(
                        _SEARCH_URL, response.status, "search failed", None, None
                    )
                data = json.loads(response.read().decode("utf-8"))
            return data.get("value", data.get("results", []))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning(
                "registry_search_attempt_failed",
                methodology_id=methodology_id,
                attempt=attempt,
                error=str(exc),
            )
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_BACKOFF_BASE**attempt)

    raise urllib.error.URLError(
        f"registry search failed after {_MAX_RETRIES} attempts: {last_error}"
    )


def _download_pdf(url: str, dest: Path) -> bool:
    """Download a single PDF. Returns True on success, False on any failure."""
    _throttle()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            dest.write_bytes(response.read())
        return True
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("registry_pdf_download_failed", url=url, error=str(exc))
        return False


def _write_manifest(
    output_dir: Path, records: list[dict[str, Any]], note: str | None = None
) -> None:
    manifest: dict[str, Any] = {"records": records}
    if note:
        manifest["note"] = note
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def download_registered_pdds(
    methodology_id: str,
    output_dir: Path | str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Download registered PDD PDFs for a methodology family.

    Attempts a live search against the public Verra registry. On any failure
    (network error, unexpected response shape, or the registry blocking
    scripted access), falls back to manual-download mode: writes an empty
    manifest with a ``note`` explaining that PDFs should be placed in
    ``output_dir`` by hand and picked up via ``refresh_manifest()``.

    Args:
        methodology_id: Methodology ID to filter on (e.g. ``"VM0051"``,
            ``"AMS-II.G"``, ``"ACM0022"``).
        output_dir: Directory to write downloaded PDFs and manifest.json into.
        limit: Maximum number of PDDs to fetch.

    Returns:
        Manifest records for whatever was actually downloaded (empty list in
        manual-download mode).
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        projects = _search_projects(methodology_id, limit)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning(
            "public_registry_search_unreachable",
            methodology_id=methodology_id,
            error=str(exc),
            note="Falling back to manual-download mode.",
        )
        _write_manifest(
            output_path,
            [],
            note=(
                f"Manual-download mode: registry search for {methodology_id!r} "
                f"was unreachable ({exc}). Download PDD PDFs from "
                f"https://registry.verra.org/app/search/VCS into this directory "
                f"by hand, then call refresh_manifest(output_dir)."
            ),
        )
        return []

    records: list[dict[str, Any]] = []
    for project in projects[:limit]:
        project_id = str(project.get("project_id") or project.get("id") or "unknown")
        title = str(project.get("title") or project.get("name") or project_id)
        pdf_url = project.get("pdd_url") or project.get("document_url") or project.get("url")
        if not pdf_url:
            logger.warning("registry_project_missing_pdf_url", project_id=project_id)
            continue

        filename = f"{_sanitize_filename(project_id)}_{_sanitize_filename(title)}.pdf"
        dest = output_path / filename
        if not _download_pdf(pdf_url, dest):
            continue

        records.append(
            {
                "project_id": project_id,
                "title": title,
                "methodology": methodology_id,
                "source_url": pdf_url,
                "local_path": str(dest),
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    if not records:
        _write_manifest(
            output_path,
            [],
            note=(
                f"Manual-download mode: registry search for {methodology_id!r} "
                f"returned no downloadable PDF documents. Download PDD PDFs from "
                f"https://registry.verra.org/app/search/VCS into this directory "
                f"by hand, then call refresh_manifest(output_dir)."
            ),
        )
        return []

    _write_manifest(output_path, records)
    return records


def refresh_manifest(output_dir: Path | str) -> list[dict[str, Any]]:
    """Scan output_dir for PDFs not already in manifest.json and add them.

    Supports manual-download mode: a human places PDF files into output_dir,
    then calls this to register them with ``source_url: "manual"``.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    manifest_path = output_path / "manifest.json"

    existing: dict[str, Any] = {"records": []}
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))

    known_paths = {record["local_path"] for record in existing.get("records", [])}
    records: list[dict[str, Any]] = list(existing.get("records", []))

    for pdf_path in sorted(output_path.glob("*.pdf")):
        if str(pdf_path) in known_paths:
            continue
        records.append(
            {
                "project_id": pdf_path.stem,
                "title": pdf_path.stem,
                "methodology": "unknown",
                "source_url": "manual",
                "local_path": str(pdf_path),
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    manifest_path.write_text(json.dumps({"records": records}, indent=2), encoding="utf-8")
    return records
