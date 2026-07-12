"""Tests for the head-to-head provider scorecard."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdd_agent.phase05.benchmark import create_demo_project_input
from pdd_agent.phase05.provider_scorecard import (
    _is_provider_available,
    run_provider_scorecard,
)


class TestIsProviderAvailable:
    def test_demo_always_available(self):
        assert _is_provider_available("demo") == (True, None)

    def test_noop_always_available(self):
        assert _is_provider_available("noop") == (True, None)

    def test_ollama_always_available(self):
        assert _is_provider_available("ollama") == (True, None)

    def test_openai_without_key_unavailable(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert _is_provider_available("openai") == (False, "missing_api_key")

    def test_openai_with_key_available(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        assert _is_provider_available("openai") == (True, None)

    def test_unknown_provider_unavailable(self):
        assert _is_provider_available("mystery") == (False, "unknown_provider")


class TestRunProviderScorecard:
    def test_scorecard_with_demo_and_noop(self, tmp_path: Path):
        input_path = create_demo_project_input(tmp_path / "demo_project.yaml")
        output_path = tmp_path / "scorecard.md"

        result_path = run_provider_scorecard(
            input_path=input_path,
            providers=["demo", "noop"],
            output_path=output_path,
        )

        assert result_path == output_path
        text = output_path.read_text(encoding="utf-8")
        assert "| demo |" in text
        assert "| noop |" in text
        header = [
            line for line in text.splitlines() if line.startswith("| Provider |")
        ][0]
        # Provider column + 7 metric columns.
        assert header.count("|") == 9

    def test_missing_key_provider_skipped_not_crashed(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        input_path = create_demo_project_input(tmp_path / "demo_project.yaml")
        output_path = tmp_path / "scorecard.md"

        run_provider_scorecard(
            input_path=input_path,
            providers=["demo", "openai"],
            output_path=output_path,
        )

        text = output_path.read_text(encoding="utf-8")
        assert "openai" in text
        assert "skipped: missing_api_key" in text
        assert "| demo |" in text

    def test_no_judge_skips_scoring(self, tmp_path: Path):
        input_path = create_demo_project_input(tmp_path / "demo_project.yaml")
        output_path = tmp_path / "scorecard.md"

        run_provider_scorecard(
            input_path=input_path,
            providers=["demo"],
            output_path=output_path,
            enable_judge=False,
        )

        text = output_path.read_text(encoding="utf-8")
        assert "| demo | 36 | 0.0% | 0.0 |" in text
