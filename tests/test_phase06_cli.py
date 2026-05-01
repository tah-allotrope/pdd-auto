"""CLI coverage for the Vietnam spreadsheet workflow."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))

from pdd_agent.cli import main


def test_map_spreadsheet_command_invokes_generator(tmp_path: Path):
    workbook = tmp_path / "sample.xlsx"
    workbook.write_bytes(b"xlsx")

    with patch(
        "sys.argv",
        [
            "pdd-agent",
            "map-spreadsheet",
            "--workbook",
            str(workbook),
            "--candidate",
            "soc-son",
            "--output-dir",
            str(tmp_path / "out"),
        ],
    ):
        with patch("pdd_agent.cli.generate_project_artifacts") as mock_generate:
            mock_generate.return_value = type(
                "Artifacts",
                (),
                {
                    "workbook_path": workbook,
                    "project_yaml_path": tmp_path / "out/project.yaml",
                    "assumptions_yaml_path": tmp_path / "out/assumptions.yaml",
                    "profile_json_path": tmp_path / "out/profile.json",
                    "snapshot_json_path": tmp_path / "out/snapshot.json",
                    "report_path": tmp_path / "out/report.md",
                },
            )()
            exit_code = main()

    assert exit_code == 0
    mock_generate.assert_called_once()


def test_fetch_workbook_command_invokes_fetcher(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    workbook = cache_dir / "workbook.xlsx"

    with patch(
        "sys.argv",
        [
            "pdd-agent",
            "fetch-workbook",
            "--cache-dir",
            str(cache_dir),
            "--force",
        ],
    ):
        with patch("pdd_agent.cli.fetch_workbook", return_value=workbook) as mock_fetch:
            exit_code = main()

    assert exit_code == 0
    mock_fetch.assert_called_once()


def test_run_vietnam_pdd_command_invokes_workflow(tmp_path: Path):
    with patch(
        "sys.argv",
        [
            "pdd-agent",
            "run-vietnam-pdd",
            "--candidate",
            "soc-son",
            "--cache-dir",
            str(tmp_path / "cache"),
        ],
    ):
        with patch("pdd_agent.cli.run_vietnam_pdd_workflow") as mock_workflow:
            mock_workflow.return_value = type(
                "Artifacts",
                (),
                {
                    "run_id": "viet-run",
                    "project_yaml_path": tmp_path / "configs/project.yaml",
                    "assumptions_yaml_path": tmp_path / "configs/assumptions.yaml",
                    "draft_run_path": tmp_path / "data/runs/viet-run.json",
                    "review_state_path": tmp_path / "data/runs/review-state-viet-run.json",
                    "docx_path": tmp_path / "reports/review-packages/project/viet-run/viet-run.docx",
                    "review_package_manifest_path": tmp_path / "reports/review-packages/project/viet-run/manifest.json",
                    "latest_docx_path": tmp_path / "reports/review-packages/project/latest.docx",
                    "validation_report_path": tmp_path / "reports/vietnam-pdd-validation.md",
                    "gap_analysis_path": tmp_path / "reports/vietnam-pdd-gap-analysis.md",
                    "runbook_path": tmp_path / "reports/vietnam-pdd-runbook.md",
                    "upload_result": None,
                },
            )()
            exit_code = main()

    assert exit_code == 0
    mock_workflow.assert_called_once()


def test_export_command_passes_review_output_dir(tmp_path: Path):
    output_dir = tmp_path / "reports" / "review-packages"
    export_path = output_dir / "project" / "run-1" / "run-1.docx"

    with patch(
        "sys.argv",
        [
            "pdd-agent",
            "export",
            "--run-id",
            "run-1",
            "--review-output-dir",
            str(output_dir),
        ],
    ):
        with patch("pdd_agent.cli.publish_docx_run_for_review", return_value=export_path) as mock_publish:
            exit_code = main()

    assert exit_code == 0
    mock_publish.assert_called_once()


def test_run_vietnam_pdd_command_passes_upload_flags(tmp_path: Path):
    with patch(
        "sys.argv",
        [
            "pdd-agent",
            "run-vietnam-pdd",
            "--candidate",
            "soc-son",
            "--cache-dir",
            str(tmp_path / "cache"),
            "--review-output-dir",
            str(tmp_path / "review-packages"),
            "--upload-review-docx",
            "--folder-id",
            "folder-123",
        ],
    ):
        with patch("pdd_agent.cli.run_vietnam_pdd_workflow") as mock_workflow:
            mock_workflow.return_value = type(
                "Artifacts",
                (),
                {
                    "run_id": "viet-run",
                    "project_yaml_path": tmp_path / "configs/project.yaml",
                    "assumptions_yaml_path": tmp_path / "configs/assumptions.yaml",
                    "draft_run_path": tmp_path / "data/runs/viet-run.json",
                    "review_state_path": tmp_path / "data/runs/review-state-viet-run.json",
                    "docx_path": tmp_path / "reports/review-packages/project/viet-run/viet-run.docx",
                    "review_package_manifest_path": tmp_path / "reports/review-packages/project/viet-run/manifest.json",
                    "latest_docx_path": tmp_path / "reports/review-packages/project/latest.docx",
                    "validation_report_path": tmp_path / "reports/vietnam-pdd-validation.md",
                    "gap_analysis_path": tmp_path / "reports/vietnam-pdd-gap-analysis.md",
                    "runbook_path": tmp_path / "reports/vietnam-pdd-runbook.md",
                    "upload_result": {"success": True, "drive_url": "https://drive.google.com/file/d/abc", "file_id": "abc", "error": None},
                },
            )()
            exit_code = main()

    assert exit_code == 0
    mock_workflow.assert_called_once()


def test_benchmark_command_supports_demo_package_output(tmp_path: Path):
    with patch(
        "sys.argv",
        [
            "pdd-agent",
            "benchmark",
            "--input",
            str(tmp_path / "demo_input.yaml"),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--demo-output-dir",
            str(tmp_path / "demo-packages"),
        ],
    ):
        with patch("pdd_agent.cli.run_demo_benchmark") as mock_benchmark:
            mock_benchmark.return_value = type(
                "Artifacts",
                (),
                {
                    "run_id": "demo-run",
                    "run_json": tmp_path / "data/runs/demo-run.json",
                    "demo_scorecard": tmp_path / "reports/demo-scorecard.md",
                    "section_diff": tmp_path / "reports/section-diff.md",
                    "export_docx": tmp_path / "reports/demo-packages/project/latest.docx",
                    "demo_package_manifest": tmp_path / "reports/demo-packages/project/run-1/manifest.json",
                    "demo_latest_docx": tmp_path / "reports/demo-packages/project/latest.docx",
                    "comparison_summary": {"matched_sections": 36},
                    "runtime_seconds": 1.2,
                },
            )()
            exit_code = main()

    assert exit_code == 0
    mock_benchmark.assert_called_once()


def test_benchmark_command_defaults_to_demo_provider(tmp_path: Path):
    with patch(
        "sys.argv",
        [
            "pdd-agent",
            "benchmark",
            "--input",
            str(tmp_path / "demo_input.yaml"),
            "--reports-dir",
            str(tmp_path / "reports"),
        ],
    ):
        with patch("pdd_agent.cli.run_demo_benchmark") as mock_benchmark:
            mock_benchmark.return_value = type(
                "Artifacts",
                (),
                {
                    "run_id": "demo-run",
                    "run_json": tmp_path / "data/runs/demo-run.json",
                    "demo_scorecard": tmp_path / "reports/demo-scorecard.md",
                    "section_diff": tmp_path / "reports/section-diff.md",
                    "export_docx": tmp_path / "reports/demo-run.docx",
                    "demo_package_manifest": None,
                    "demo_latest_docx": None,
                    "comparison_summary": {"matched_sections": 36},
                    "runtime_seconds": 1.2,
                },
            )()
            exit_code = main()

    assert exit_code == 0
    mock_benchmark.assert_called_once()
    assert mock_benchmark.call_args.kwargs["provider_name"] == "demo"
