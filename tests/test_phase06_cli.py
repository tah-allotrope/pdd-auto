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
