"""Tests for the head-to-head provider scorecard."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


from pdd_agent.phase05.benchmark import create_demo_project_input
from pdd_agent.phase05.provider_scorecard import (
    ProviderScorecardRow,
    _count_failed_sections,
    _is_provider_available,
    _render_grounding_block,
    _resolve_providers,
    run_provider_scorecard,
)


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

        def fake_availability(name):
            # Force every provider this dev machine might genuinely have
            # installed (Ollama, the Claude Code CLI) to "unavailable" so
            # this test never depends on real local tool state — without
            # this, a machine with `claude` on PATH would let "claude-code"
            # leak into available_providers and get selected as a REAL
            # cross-judge for the demo row, firing an actual (billed)
            # `claude` subprocess call. This exact leak happened once.
            if name in ("ollama", "claude-code"):
                return False, f"no_{name.replace('-', '_')}"
            return _is_provider_available(name)

        monkeypatch.setattr(
            "pdd_agent.phase05.provider_scorecard._is_provider_available",
            fake_availability,
        )
        # Defense-in-depth: even if availability leaked, force the
        # deterministic judge so no provider is ever cross-judged for real.
        monkeypatch.setenv("PDD_JUDGE_PROVIDER", "demo")
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


class TestGroundingProvenance:
    def test_grounding_block_rendered(self, tmp_path: Path):
        input_path = create_demo_project_input(tmp_path / "demo_project.yaml")
        output_path = tmp_path / "scorecard.md"

        run_provider_scorecard(
            input_path=input_path,
            providers=["demo"],
            output_path=output_path,
        )

        text = output_path.read_text(encoding="utf-8")
        assert "## Grounding" in text
        assert "- Retrieval index: " in text
        assert "- Corpus documents: " in text
        assert "- Calc methodology: " in text

    def test_grounding_block_omitted_when_nothing_ran(self):
        assert _render_grounding_block([]) == []

    def test_grounding_block_reports_absent_calc(self):
        row = ProviderScorecardRow(provider="demo", retrieval_index="x.db", corpus_doc_count=3)
        lines = _render_grounding_block([row])
        assert "- Calc methodology: none (no calc engine dispatched)" in lines


class TestProviderScorecardRowFields:
    def test_new_fields_default_correctly(self):
        row = ProviderScorecardRow(provider="demo")
        assert row.sections_failed == 0
        assert row.judge_provider == ""
        assert row.retrieval_index == ""
        assert row.corpus_doc_count == 0
        assert row.calc_methodology == ""
