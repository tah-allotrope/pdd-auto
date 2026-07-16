"""Tests for the head-to-head provider scorecard."""

from __future__ import annotations

import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch


from pdd_agent.phase05.benchmark import create_demo_project_input
from pdd_agent.phase05.provider_scorecard import (
    ProviderScorecardRow,
    _count_failed_sections,
    _is_provider_available,
    _resolve_providers,
    _select_judge_provider,
    run_provider_scorecard,
)


class TestIsProviderAvailable:
    def test_demo_always_available(self):
        assert _is_provider_available("demo") == (True, None)

    def test_noop_always_available(self):
        assert _is_provider_available("noop") == (True, None)

    def test_ollama_unreachable_is_unavailable(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            assert _is_provider_available("ollama") == (False, "ollama_unreachable")

    def test_ollama_reachable_is_available(self):
        response = MagicMock()
        response.__enter__ = MagicMock(return_value=response)
        response.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=response):
            assert _is_provider_available("ollama") == (True, None)

    def test_openai_without_key_unavailable(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert _is_provider_available("openai") == (False, "missing_api_key")

    def test_openai_with_key_but_no_cost_ceiling_unavailable(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("PDD_MAX_COST_USD", raising=False)
        assert _is_provider_available("openai") == (False, "missing_cost_ceiling")

    def test_openai_with_key_and_cost_ceiling_available(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("PDD_MAX_COST_USD", "5.0")
        assert _is_provider_available("openai") == (True, None)

    def test_unknown_provider_unavailable(self):
        assert _is_provider_available("mystery") == (False, "unknown_provider")


class TestSelectJudgeProvider:
    def test_no_other_candidate_falls_back_to_demo(self, monkeypatch):
        monkeypatch.delenv("PDD_JUDGE_PROVIDER", raising=False)
        assert _select_judge_provider("ollama", ["demo", "ollama"]) == ("demo", False)

    def test_prefers_anthropic_over_drafting_provider(self, monkeypatch):
        monkeypatch.delenv("PDD_JUDGE_PROVIDER", raising=False)
        assert _select_judge_provider("ollama", ["demo", "ollama", "anthropic"]) == (
            "anthropic",
            True,
        )

    def test_skips_self_and_picks_next_in_preference_order(self, monkeypatch):
        monkeypatch.delenv("PDD_JUDGE_PROVIDER", raising=False)
        assert _select_judge_provider("anthropic", ["anthropic", "openai"]) == ("openai", True)

    def test_env_override_wins(self, monkeypatch):
        monkeypatch.setenv("PDD_JUDGE_PROVIDER", "demo")
        assert _select_judge_provider("anthropic", ["anthropic", "openai"]) == ("demo", False)


class TestCountFailedSections:
    def test_counts_only_matching_error_prefix(self):
        sections = [
            MagicMock(text="[OLLAMA ERROR — 1.1] boom"),
            MagicMock(text="Normal drafted text"),
            MagicMock(text="[OLLAMA ERROR — 1.2] boom"),
            MagicMock(text="[OLLAMA ERROR — 1.3] boom"),
            MagicMock(text="[ANTHROPIC ERROR — 1.4] different provider, not counted"),
        ]
        assert _count_failed_sections(sections, "ollama") == 3


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
        assert "Sections failed" in text
        assert "Judge" in text
        header = [line for line in text.splitlines() if line.startswith("| Provider |")][0]
        # Provider column + 9 metric columns.
        assert header.count("|") == 11

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
        assert "| demo | 36 | 0 | 0.0% | 0.0 |" in text

    def test_provider_crash_isolated_not_fatal(self, tmp_path: Path, monkeypatch):
        """A crashing provider must not abort the whole scorecard (RISK-04-02)."""
        from pdd_agent.agent.section_orchestrator import SectionOrchestrator as RealOrchestrator

        input_path = create_demo_project_input(tmp_path / "demo_project.yaml")
        output_path = tmp_path / "scorecard.md"

        monkeypatch.setattr(
            "pdd_agent.phase05.provider_scorecard._is_provider_available",
            lambda name: (True, None),
        )
        # Force the deterministic judge for every row. Without this, marking
        # "ollama" available for the "demo" row's post-hoc judge selection
        # would pick real Ollama as judge (use_llm=True) and attempt a real,
        # unmocked network call — exactly the CON-001 violation this test
        # must not reproduce.
        monkeypatch.setenv("PDD_JUDGE_PROVIDER", "demo")

        class _FakeOrchestrator:
            def __init__(self, provider, project_input, token_budget, enable_judge):
                self.redraft_count = 0
                self._real = (
                    None
                    if getattr(provider, "name", None) == "ollama"
                    else RealOrchestrator(
                        provider=provider,
                        project_input=project_input,
                        token_budget=token_budget,
                        enable_judge=enable_judge,
                    )
                )

            def run(self):
                if self._real is None:
                    raise RuntimeError("boom")
                return self._real.run()

        with patch(
            "pdd_agent.phase05.provider_scorecard.SectionOrchestrator",
            side_effect=_FakeOrchestrator,
        ):
            run_provider_scorecard(
                input_path=input_path,
                providers=["demo", "ollama"],
                output_path=output_path,
            )

        text = output_path.read_text(encoding="utf-8")
        assert "| demo | 36 |" in text
        assert "provider_error: boom" in text


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


class TestProviderScorecardRowFields:
    def test_new_fields_default_correctly(self):
        row = ProviderScorecardRow(provider="demo")
        assert row.sections_failed == 0
        assert row.judge_provider == ""
