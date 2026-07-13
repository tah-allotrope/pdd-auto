"""Optional PDF export via LibreOffice CLI conversion.

Converts a DOCX file to PDF using LibreOffice's headless mode.
Falls back gracefully when LibreOffice is not installed.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import structlog

logger = structlog.get_logger()


class PDFExportError(Exception):
    """Raised when PDF conversion fails."""


def _find_libreoffice() -> str | None:
    """Find LibreOffice executable on the system."""
    for candidate in ("libreoffice", "soffice", "soffice.exe"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


def is_libreoffice_available() -> bool:
    """Check if LibreOffice is installed and accessible."""
    return _find_libreoffice() is not None


def export_docx_to_pdf(
    docx_path: Path,
    output_dir: Path | None = None,
    timeout_seconds: int = 120,
) -> Path:
    """Convert a DOCX file to PDF using LibreOffice headless mode.

    Args:
        docx_path: Path to the source DOCX file.
        output_dir: Directory for the PDF output. Defaults to same directory as DOCX.
        timeout_seconds: Maximum time for the conversion process.

    Returns:
        Path to the generated PDF file.

    Raises:
        PDFExportError: If LibreOffice is not available or conversion fails.
    """
    docx_path = Path(docx_path)
    if not docx_path.exists():
        raise PDFExportError(f"DOCX file not found: {docx_path}")

    lo_path = _find_libreoffice()
    if lo_path is None:
        raise PDFExportError(
            "LibreOffice not found. Install LibreOffice for PDF export, or use DOCX output instead."
        )

    if output_dir is None:
        output_dir = docx_path.parent
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        lo_path,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(docx_path),
    ]

    logger.info(
        "pdf_export_start",
        docx_path=str(docx_path),
        output_dir=str(output_dir),
    )

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        raise PDFExportError(f"LibreOffice conversion timed out after {timeout_seconds}s")
    except OSError as exc:
        raise PDFExportError(f"Failed to run LibreOffice: {exc}") from exc

    if result.returncode != 0:
        raise PDFExportError(
            f"LibreOffice conversion failed (exit {result.returncode}): {result.stderr.strip()}"
        )

    pdf_path = output_dir / docx_path.with_suffix(".pdf").name
    if not pdf_path.exists():
        raise PDFExportError(
            f"PDF file not created at expected path: {pdf_path}. "
            f"LibreOffice output: {result.stdout.strip()}"
        )

    logger.info("pdf_export_complete", pdf_path=str(pdf_path))
    return pdf_path
