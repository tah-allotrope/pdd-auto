"""Reviewer-facing publication helpers for PDD review packages."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil


@dataclass(frozen=True)
class ReviewPackagePaths:
    project_slug: str
    package_dir: Path
    docx_path: Path
    latest_docx_path: Path
    manifest_path: Path


def publish_review_package(
    run_id: str,
    project_name: str,
    docx_path: Path | str,
    validation_report_path: Path | str,
    gap_analysis_path: Path | str,
    assumption_burden_path: Path | str,
    assumptions_yaml_path: Path | str,
    project_yaml_path: Path | str,
    output_root: Path | str,
) -> ReviewPackagePaths:
    """Copy review artifacts into a stable reviewer-facing package."""
    source_docx = Path(docx_path)
    if not source_docx.exists():
        raise FileNotFoundError(f"DOCX review artifact not found at `{source_docx}`")

    root = Path(output_root)
    project_slug = _slugify(project_name)
    package_dir = root / project_slug / run_id
    package_dir.mkdir(parents=True, exist_ok=True)

    published_docx_path = package_dir / f"{run_id}.docx"
    shutil.copy2(source_docx, published_docx_path)

    published_validation_path = _copy_if_exists(validation_report_path, package_dir)
    published_gap_analysis_path = _copy_if_exists(gap_analysis_path, package_dir)
    published_assumption_burden_path = _copy_if_exists(assumption_burden_path, package_dir)
    published_assumptions_yaml_path = _copy_if_exists(assumptions_yaml_path, package_dir)
    published_project_yaml_path = _copy_if_exists(project_yaml_path, package_dir)

    manifest = {
        "run_id": run_id,
        "project_name": project_name,
        "project_slug": project_slug,
        "published_docx": str(published_docx_path),
        "source_docx": str(source_docx),
        "validation_report": str(published_validation_path or Path(validation_report_path)),
        "gap_analysis": str(published_gap_analysis_path or Path(gap_analysis_path)),
        "assumption_burden": str(published_assumption_burden_path or Path(assumption_burden_path)),
        "assumptions_yaml": str(published_assumptions_yaml_path or Path(assumptions_yaml_path)),
        "project_yaml": str(published_project_yaml_path or Path(project_yaml_path)),
    }
    manifest_path = package_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    latest_dir = root / project_slug
    latest_dir.mkdir(parents=True, exist_ok=True)
    latest_docx_path = latest_dir / "latest.docx"
    shutil.copy2(published_docx_path, latest_docx_path)

    return ReviewPackagePaths(
        project_slug=project_slug,
        package_dir=package_dir,
        docx_path=published_docx_path,
        latest_docx_path=latest_docx_path,
        manifest_path=manifest_path,
    )


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "review-package"


def _copy_if_exists(path: Path | str, destination_dir: Path) -> Path | None:
    source = Path(path)
    if not source.exists():
        return None
    destination = destination_dir / source.name
    shutil.copy2(source, destination)
    return destination
