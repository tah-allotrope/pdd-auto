"""Tests for the head-to-head provider scorecard."""

from __future__ import annotations

from pathlib import Path


from pdd_agent.phase05.benchmark import create_demo_project_input
from pdd_agent.phase05.provider_scorecard import (
    _is_provider_available,
    _resolve_providers,
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
        header = [line for line in text.splitlines() if line.startswith("| Provider |")][0]
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


class TestResolveProviders:
    def test_auto_expands_to_all_known(self):
        resolved = _resolve_providers("auto")
        assert "demo" in resolved
        assert "ollama" in resolved
        assert "openai" in resolved
        assert "anthropic" in resolved

    def test_explicit_list_passthrough(self):
        resolved = _resolve_providers(["demo", "openai"])
        assert resolved == ["demo", "openai"]

    def test_comma_string_parsed(self):
        resolved = _resolve_providers("demo, ollama")
        assert resolved == ["demo", "ollama"]

    def test_auto_as_list(self):
        resolved = _resolve_providers(["auto"])
        assert "demo" in resolved
        assert len(resolved) >= 3


class TestAutoModeScorecard:
    def test_auto_mode_skips_unkeyed_providers(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(
            "pdd_agent.phase05.provider_scorecard._is_provider_available",
            lambda name: (False, "no_ollama") if name == "ollama" else _is_provider_available(name),
        )
        input_path = create_demo_project_input(tmp_path / "demo_project.yaml")
        output_path = tmp_path / "scorecard.md"

        run_provider_scorecard(
            input_path=input_path,
            providers="auto",
            output_path=output_path,
        )

        text = output_path.read_text(encoding="utf-8")
        assert "| demo |" in text
        assert "Providers ran:" in text
        assert "Providers skipped:" in text
        assert "Skipped providers" in text
        assert "openai" in text
        assert "anthropic" in text
