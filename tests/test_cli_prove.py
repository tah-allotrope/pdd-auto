"""Tests for the `prove` CLI subcommand's project-alias resolution."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from pdd_agent.cli import _run_prove


class _StubLogger:
    def info(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class TestProveProjectAlias:
    def test_inegol_alias_resolves_to_inegol_config_not_socson(self, tmp_path):
        """Regression test: `inegol` previously pointed at demo_socson_like.yaml."""
        args = Namespace(
            project="inegol",
            providers="demo",
            output=str(tmp_path / "scorecard.md"),
            no_judge=True,
        )

        with patch("pdd_agent.phase05.provider_scorecard.run_provider_scorecard") as mock_run:
            mock_run.return_value = Path(args.output)
            _run_prove(args, _StubLogger())

        called_input_path = mock_run.call_args.kwargs["input_path"]
        assert called_input_path == Path("configs/demo/inegol_project_input.yaml")

    def test_socson_and_rice_aliases_unchanged(self, tmp_path):
        for alias, expected in (
            ("socson", "configs/projects/demo_socson_like.yaml"),
            ("rice", "configs/projects/rice_vm0051_pilot.yaml"),
        ):
            args = Namespace(
                project=alias,
                providers="demo",
                output=str(tmp_path / f"scorecard-{alias}.md"),
                no_judge=True,
            )
            with patch("pdd_agent.phase05.provider_scorecard.run_provider_scorecard") as mock_run:
                mock_run.return_value = Path(args.output)
                _run_prove(args, _StubLogger())

            assert mock_run.call_args.kwargs["input_path"] == Path(expected)
