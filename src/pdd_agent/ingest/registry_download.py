"""Public-registry PDD downloader (skeleton).

This module defines the intended interface for fetching registered PDD PDFs
from the public Verra / CDM registry for a given methodology family.  It does
not perform live downloads because:

- Public registry endpoints require rate-limit-resilient scraping.
- No API keys or external registry downloads are available in this environment.
- The rest of the pipeline (`normalize.py` -> `bucket.py` -> `retrieval/index.py`)
  can operate on manually-curated PDFs until the downloader is implemented.

When implemented, `download_registered_pdds` should:

1. Query the registry search page / API for the supplied `methodology_id`.
2. Resolve project-detail pages and PDF links.
3. Download up to `limit` PDD PDFs into `output_dir`.
4. Return a list of local file paths (or metadata dicts) for downstream
   normalization and indexing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


def download_registered_pdds(
    methodology_id: str,
    output_dir: Path | str,
    limit: int = 10,
) -> list[Any]:
    """Stub: download registered PDD PDFs for a methodology family.

    Args:
        methodology_id: Methodology ID to filter on (e.g. ``"VM0051"``,
            ``"AMS-II.G"``, ``"ACM0022"``).
        output_dir: Directory to write downloaded PDFs into.
        limit: Maximum number of PDDs to fetch.

    Returns:
        Empty list.  A full implementation would return downloaded file paths
        or metadata records.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    logger.warning(
        "public_registry_download_not_yet_implemented",
        methodology_id=methodology_id,
        output_dir=str(output_path),
        limit=limit,
        note="Manual download of registered PDDs is required until this stub is implemented.",
    )
    return []
