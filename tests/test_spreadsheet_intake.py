"""Tests for spreadsheet download and intake helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))

from pdd_agent.phase06.spreadsheet_mapper import fetch_workbook


def _write_mapping(path: Path) -> Path:
    payload = {
        "source_file": {
            "drive_file_id": "spreadsheet-123",
            "expected_name": "WtE plants carbon model early draft.xlsx",
        },
        "selection": {
            "sheet_name": "Projects",
            "header_row": 1,
            "candidate_column": "project_name",
            "country_column": "Province/Country",
            "methodology_column": "VCS Methodology",
            "candidates": {},
        },
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_fetch_workbook_downloads_to_stable_cache(tmp_path: Path):
    mapping_path = _write_mapping(tmp_path / "mapping.yaml")
    cache_dir = tmp_path / "cache"

    with patch("pdd_agent.phase06.spreadsheet_mapper.download_blob") as mock_download:

        def _side_effect(file_id: str, output_path: Path, mime_type: str):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"xlsx")
            return output_path

        mock_download.side_effect = _side_effect

        workbook_path = fetch_workbook(mapping_path, cache_dir=cache_dir, force=True)

    assert workbook_path == cache_dir / "WtE_plants_carbon_model_early_draft.xlsx"
    assert workbook_path.exists()
    mock_download.assert_called_once_with(
        "spreadsheet-123",
        workbook_path,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def test_fetch_workbook_reuses_existing_cached_file(tmp_path: Path):
    mapping_path = _write_mapping(tmp_path / "mapping.yaml")
    cache_dir = tmp_path / "cache"
    workbook_path = cache_dir / "WtE_plants_carbon_model_early_draft.xlsx"
    workbook_path.parent.mkdir(parents=True, exist_ok=True)
    workbook_path.write_bytes(b"cached-xlsx")

    with patch("pdd_agent.phase06.spreadsheet_mapper.download_blob") as mock_download:
        cached_path = fetch_workbook(mapping_path, cache_dir=cache_dir, force=False)

    assert cached_path == workbook_path
    mock_download.assert_not_called()
