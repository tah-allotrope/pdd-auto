"""Run the Phase 01-02 Vietnam WTE spreadsheet mapping workflow."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))

from pdd_agent.phase06.spreadsheet_mapper import (
    DEFAULT_MAPPING_CONFIG,
    DEFAULT_SPREADSHEET_CACHE_DIR,
    fetch_workbook,
    generate_project_artifacts,
)


def main() -> None:
    workbook_path = fetch_workbook(DEFAULT_MAPPING_CONFIG, cache_dir=DEFAULT_SPREADSHEET_CACHE_DIR)
    artifacts = generate_project_artifacts(
        workbook_path=workbook_path, mapping_config_path=DEFAULT_MAPPING_CONFIG
    )
    print(f"Workbook: {artifacts.workbook_path}")
    print(f"Project YAML: {artifacts.project_yaml_path}")
    print(f"Assumptions YAML: {artifacts.assumptions_yaml_path}")
    print(f"Profile JSON: {artifacts.profile_json_path}")
    print(f"Snapshot JSON: {artifacts.snapshot_json_path}")
    print(f"Report: {artifacts.report_path}")


if __name__ == "__main__":
    main()
