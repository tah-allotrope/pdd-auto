"""Run the full Vietnam WTE spreadsheet-to-DOCX workflow."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))

from pdd_agent.phase06.vietnam_workflow import run_vietnam_pdd_workflow


def main() -> int:
    artifacts = run_vietnam_pdd_workflow()
    print(f"Workbook: {artifacts.workbook_path}")
    print(f"Project YAML: {artifacts.project_yaml_path}")
    print(f"Assumptions YAML: {artifacts.assumptions_yaml_path}")
    print(f"Profile JSON: {artifacts.profile_json_path}")
    print(f"Snapshot JSON: {artifacts.snapshot_json_path}")
    print(f"Source Report: {artifacts.source_report_path}")
    print(f"Run ID: {artifacts.run_id}")
    print(f"Draft Run: {artifacts.draft_run_path}")
    print(f"Review State: {artifacts.review_state_path}")
    print(f"Assumption Burden: {artifacts.assumption_burden_path}")
    print(f"Review DOCX: {artifacts.docx_path}")
    print(f"Review Package Manifest: {artifacts.review_package_manifest_path}")
    print(f"Latest Review DOCX: {artifacts.latest_docx_path}")
    print(f"Validation Report: {artifacts.validation_report_path}")
    print(f"Gap Analysis: {artifacts.gap_analysis_path}")
    print(f"Runbook: {artifacts.runbook_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
