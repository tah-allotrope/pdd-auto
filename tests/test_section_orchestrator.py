"""Tests for SectionOrchestrator and LLM provider abstraction."""

from __future__ import annotations


import urllib.error
from pathlib import Path
from unittest.mock import MagicMock

from pdd_agent.llm.provider import (
    DraftSection,
    DraftRun,
    NoopProvider,
    ProviderRegistry,
    get_provider_registry,
    ModelConfig,
    configure_provider,
)
from pdd_agent.agent.section_orchestrator import SectionOrchestrator
from pdd_agent.review.states import ReviewStateStore


def _force_only_demo_judge_available(monkeypatch) -> None:
    """Force resolve_judge_provider() to fall back to the deterministic demo judge.

    Without this, tests that enable the in-loop judge would probe real
    provider availability for real — and on a machine with the `claude` CLI
    on PATH (as this repo's reference dev machine has), or after
    tests/test_claude_code_provider.py has registered a real
    ClaudeCodeProvider under "claude-code" in the process-global provider
    registry, the judge would actually shell out to the live CLI during a
    pytest run. See judge_selection.is_provider_available for what each of
    these four patches forces unavailable.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("pdd_agent.llm.judge_selection.shutil.which", lambda name: None)
    monkeypatch.setattr(
        "pdd_agent.llm.judge_selection.urllib.request.urlopen",
        MagicMock(side_effect=urllib.error.URLError("refused")),
    )


class TestNoopProvider:
    def test_draft_section_returns_placeholder(self):
        provider = NoopProvider()
        result = provider.draft_section(
            section_id="3.4",
            sub_section_id="",
            prompt="Write about baseline scenario",
            provenance=["[CORPUS: VCS_Soc Son, 3.4 Baseline Scenario]"],
        )
        assert result.section_id == "3.4"
        assert result.confidence == "UNSUPPORTED"
        assert "[PLACEHOLDER" in result.text
        assert len(result.issues) == 1
        assert "REVIEW REQUIRED" in result.issues[0]

    def test_draft_section_includes_provenance_in_issues(self):
        provider = NoopProvider()
        result = provider.draft_section(
            section_id="1.1",
            sub_section_id="",
            prompt="Write summary",
            provenance=["[CORPUS: VCS_Bergama, 1.1 Summary]"],
        )
        assert any("REVIEW REQUIRED" in issue for issue in result.issues)

    def test_close_is_noop(self):
        provider = NoopProvider()
        provider.close()


class TestProviderRegistry:
    def test_get_default_noop(self):
        registry = get_provider_registry()
        p = registry.default()
        assert isinstance(p, NoopProvider)

    def test_register_and_retrieve(self):
        registry = ProviderRegistry()
        provider = NoopProvider()
        registry.register("test", provider)
        assert registry.get("test") is provider

    def test_unknown_provider_falls_back_to_noop(self):
        registry = get_provider_registry()
        p = registry.get("completely_unknown_provider")
        assert isinstance(p, NoopProvider)


class TestDraftRun:
    def test_add_sections(self):
        run = DraftRun(run_id="test-001", project_name="Test WTE")
        s1 = DraftSection("1.1", "", "Summary text", "HIGH", [], [], "noop")
        s2 = DraftSection("3.4", "", "Baseline text", "HIGH", [], [], "noop")
        run.add(s1)
        run.add(s2)
        assert len(run.sections) == 2

    def test_to_dict(self):
        run = DraftRun(run_id="test-002", project_name="Test")
        run.add(DraftSection("1.1", "", "text", "HIGH", ["[CORPUS: doc, h]"], [], "noop"))
        d = run.to_dict()
        assert d["run_id"] == "test-002"
        assert len(d["sections"]) == 1
        assert d["sections"][0]["section_id"] == "1.1"

    def test_summary_counts(self):
        run = DraftRun(run_id="test-003", project_name="Test")
        run.add(DraftSection("1.1", "", "t1", "HIGH", [], [], "noop"))
        run.add(DraftSection("3.4", "", "t2", "LOW", [], [], "noop"))
        run.add(DraftSection("3.4", "", "t3", "HIGH", [], [], "noop"))
        summary = run.summary()
        assert summary["total_sections"] == 3
        assert summary["by_confidence"]["HIGH"] == 2
        assert summary["total_issues"] == 0


class TestSectionOrchestratorInit:
    def test_init_with_defaults(self):
        orch = SectionOrchestrator()
        assert orch.run_id.startswith("run-")
        assert orch.draft_run is not None
        assert orch.draft_run.provider == "noop"

    def test_init_with_provider(self):
        provider = NoopProvider()
        orch = SectionOrchestrator(provider=provider)
        assert orch.draft_run.provider == "noop"

    def test_schema_loads_all_5_sections(self):
        orch = SectionOrchestrator()
        assert len(orch._schema["sections"]) == 5


class TestSectionOrchestratorDrafting:
    def test_draft_single_section(self):
        orch = SectionOrchestrator()
        result = orch.draft_section("1.1", "")
        assert result.section_id == "1.1"
        assert result.sub_section_id == ""
        assert result.confidence in ("HIGH", "MEDIUM", "LOW", "UNSUPPORTED")

    def test_draft_is_cached(self):
        orch = SectionOrchestrator()
        r1 = orch.draft_section("1.1", "")
        r2 = orch.draft_section("1.1", "")
        assert r1 is r2

    def test_draft_with_examples(self):
        orch = SectionOrchestrator()
        fake_examples = [
            {
                "document_name": "VCS_Soc Son",
                "canonical_heading": "Summary Description",
                "text": "The project involves construction of a waste-to-energy facility.",
            }
        ]
        result = orch.draft_section("1.1", "", examples=fake_examples)
        assert result.section_id == "1.1"
        assert len(result.provenance) == 1

    def test_draft_high_review_creates_issue_when_no_examples(self):
        orch = SectionOrchestrator()
        result = orch.draft_section("3.5", "")  # CRITICAL additionality
        assert any("REVIEW REQUIRED" in i or "CRITICAL" in i for i in result.issues)

    def test_draft_all_sections_returns_list(self):
        orch = SectionOrchestrator()
        results = orch.draft_all_sections()
        assert isinstance(results, list)
        assert len(results) >= 20  # at least 20 sub-sections

    def test_run_returns_draft_run(self):
        orch = SectionOrchestrator()
        run = orch.run()
        assert isinstance(run, DraftRun)
        assert run.run_id == orch.run_id
        assert len(run.sections) >= 20

    def test_drafted_sections_dict(self):
        orch = SectionOrchestrator()
        orch.draft_section("1.2", "")
        assert "1.2/" in orch.drafted_sections or any("1.2" in k for k in orch.drafted_sections)

    def test_attached_assumptions_are_persisted_on_draft_sections(self):
        orch = SectionOrchestrator()
        orch.attach_assumption_register(
            {
                "assumptions": [
                    {
                        "field_path": "project.project_name",
                        "value": "Soc Son waste to power plant project",
                        "source_type": "spreadsheet",
                        "confidence": "high",
                    },
                    {
                        "field_path": "technology.installed_capacity_mw",
                        "value": 52.115,
                        "source_type": "synthetic_assumption",
                        "confidence": "low",
                    },
                ],
                "guardrails": {"blocked_review_paths": []},
            }
        )

        result = orch.draft_section("1", "1.1", examples=[])

        assert len(result.fact_provenance) >= 2
        assert len(result.synthetic_uses) == 1
        assert result.output_references[0]["type"] == "section narrative"

    def test_high_review_section_with_blocked_synthetic_inputs_stays_review_gated(self):
        orch = SectionOrchestrator()
        orch.attach_assumption_register(
            {
                "assumptions": [
                    {
                        "field_path": "quantification.baseline_emissions_tco2e_per_year",
                        "value": 594076.0,
                        "source_type": "synthetic_assumption",
                        "confidence": "low",
                    }
                ],
                "guardrails": {
                    "blocked_review_paths": ["quantification.baseline_emissions_tco2e_per_year"]
                },
            }
        )

        result = orch.draft_section("4", "4.1", examples=[])

        assert result.confidence == "LOW"
        assert any("review-gated synthetic inputs" in issue for issue in result.issues)

    def test_run_review_records_synthetic_gate_in_review_state(self, tmp_path: Path):
        orch = SectionOrchestrator(
            run_id="synthetic-review-run",
            assumption_burden_path=tmp_path / "assumption-burden.md",
        )
        orch.attach_assumption_register(
            {
                "assumptions": [
                    {
                        "field_path": "quantification.baseline_emissions_tco2e_per_year",
                        "value": 594076.0,
                        "source_type": "synthetic_assumption",
                        "confidence": "low",
                    }
                ],
                "guardrails": {
                    "blocked_review_paths": ["quantification.baseline_emissions_tco2e_per_year"]
                },
            }
        )
        orch.draft_section("4", "4.1", examples=[])
        review = orch.run_review()

        store = ReviewStateStore.load("synthetic-review-run")

        assert Path(review["assumption_burden_path"]).exists()
        assert store.sections["4/4.1"].state.value == "needs-domain-review"
        assert any(
            "Synthetic review gate" in note for note in store.sections["4/4.1"].reviewer_notes
        )


class TestProviderConfigure:
    def test_configure_noop(self):
        configure_provider(ModelConfig(provider_name="noop", model_name="none"))
        registry = get_provider_registry()
        assert "noop" in registry.providers


class _CitationFailingProvider:
    """Fake provider that always returns a draft with an invalid evidence citation."""

    name = "fake-citation-fail"

    def draft_section(
        self,
        section_id: str,
        sub_section_id: str,
        prompt: str,
        provenance: list,
        max_chars: int = 4000,
    ):
        return DraftSection(
            section_id=section_id,
            sub_section_id=sub_section_id or "",
            text="Draft text with fabricated citation [E999].",
            confidence="HIGH",
            provenance=provenance,
            issues=[],
            provider=self.name,
        )

    def close(self):
        pass


class TestSectionOrchestratorRedraft:
    def test_default_max_redraft_attempts(self):
        orch = SectionOrchestrator()
        assert orch._max_redraft_attempts == 3
        assert orch._enable_judge is False

    def test_judge_redraft_loop_parks_failed_section(self, tmp_path: Path, monkeypatch):
        from pathlib import Path

        import yaml
        from schemas.project_input import EvidenceItem, EvidenceRegistry, ProjectInput

        _force_only_demo_judge_available(monkeypatch)

        project_yaml = (
            Path(__file__).parent.parent / "configs" / "projects" / "demo_socson_like.yaml"
        )
        with open(project_yaml, encoding="utf-8") as f:
            project_input = ProjectInput.model_validate(yaml.safe_load(f))
        project_input.evidence_registry = EvidenceRegistry(
            items=[EvidenceItem(evidence_id="E001", source_type="user_input", description="ok")]
        )

        orch = SectionOrchestrator(
            provider=_CitationFailingProvider(),
            project_input=project_input,
            run_id="redraft-fail-run",
            enable_judge=True,
            max_redraft_attempts=2,
        )
        draft = orch.draft_section("1", "1.1")

        assert draft.confidence == "UNSUPPORTED"
        assert any("JUDGE REDRAFT FAILED" in issue for issue in draft.issues)
        assert any("attempts" in note for note in orch.draft_run.notes)

    def test_manual_redraft_section_invokes_judge(self, monkeypatch):
        _force_only_demo_judge_available(monkeypatch)
        orch = SectionOrchestrator()
        _first = orch.draft_section("1", "1.1")
        second = orch.redraft_section("1", "1.1")
        assert second.section_id == "1"
        assert second.sub_section_id == "1.1"


class TestRedraftJudgeSelection:
    """Regression coverage for the in-loop redraft judge never self-judging."""

    def test_never_self_judges_when_alternative_available(self, monkeypatch):
        recorded_kwargs: dict = {}

        def fake_llm_judge(*args, **kwargs):
            recorded_kwargs.update(kwargs)
            judge = MagicMock()
            judge.judge_section.return_value = MagicMock(
                passed=True, categories={"critical": [], "advisory": []}, score=95
            )
            return judge

        monkeypatch.setattr(
            "pdd_agent.agent.section_orchestrator.resolve_judge_provider",
            lambda drafting_provider: ("anthropic", True),
        )
        monkeypatch.setattr(
            "pdd_agent.agent.section_orchestrator.LLMJudge",
            fake_llm_judge,
        )

        orch = SectionOrchestrator(
            provider=_CitationFailingProvider(),
            enable_judge=True,
        )
        orch.draft_section("1", "1.1")

        assert recorded_kwargs["provider_name"] == "anthropic"
        assert recorded_kwargs["provider_name"] != "fake-citation-fail"
        assert recorded_kwargs["use_llm"] is True

    def test_falls_back_to_demo_when_no_alternative(self, monkeypatch):
        recorded_kwargs: dict = {}

        def fake_llm_judge(*args, **kwargs):
            recorded_kwargs.update(kwargs)
            judge = MagicMock()
            judge.judge_section.return_value = MagicMock(
                passed=True, categories={"critical": [], "advisory": []}, score=95
            )
            return judge

        monkeypatch.setattr(
            "pdd_agent.agent.section_orchestrator.resolve_judge_provider",
            lambda drafting_provider: ("demo", False),
        )
        monkeypatch.setattr(
            "pdd_agent.agent.section_orchestrator.LLMJudge",
            fake_llm_judge,
        )

        orch = SectionOrchestrator(
            provider=_CitationFailingProvider(),
            enable_judge=True,
        )
        orch.draft_section("1", "1.1")

        assert recorded_kwargs["provider_name"] == "demo"
        assert recorded_kwargs["use_llm"] is False

    def test_caches_judge_provider_across_sections(self, monkeypatch):
        resolve_calls: list[str] = []

        def fake_resolve(drafting_provider):
            resolve_calls.append(drafting_provider)
            return ("anthropic", True)

        def fake_llm_judge(*args, **kwargs):
            judge = MagicMock()
            judge.judge_section.return_value = MagicMock(
                passed=True, categories={"critical": [], "advisory": []}, score=95
            )
            return judge

        monkeypatch.setattr(
            "pdd_agent.agent.section_orchestrator.resolve_judge_provider", fake_resolve
        )
        monkeypatch.setattr("pdd_agent.agent.section_orchestrator.LLMJudge", fake_llm_judge)

        orch = SectionOrchestrator(
            provider=_CitationFailingProvider(),
            enable_judge=True,
        )
        orch.draft_section("1", "1.1")
        orch.draft_section("1", "1.2")

        assert len(resolve_calls) == 1


class TestCalcResultPersistence:
    def _soc_son_project_input(self):
        import yaml

        from schemas.project_input import ProjectInput

        root = Path(__file__).parent.parent
        with open(
            root / "configs" / "projects" / "vietnam_socson_from_sheet.yaml", encoding="utf-8"
        ) as f:
            return ProjectInput.model_validate(yaml.safe_load(f))

    def test_calc_result_round_trips_through_run_json(self, tmp_path: Path):
        from pdd_agent.calc.dispatch import compute_for

        pi = self._soc_son_project_input()
        calc_result = compute_for(pi)
        assert calc_result is not None

        orch = SectionOrchestrator(provider=NoopProvider(), project_input=pi, runs_dir=tmp_path)
        orch.set_calc_result(calc_result)
        orch.run()
        orch.draft_run.save(output_dir=tmp_path)

        loaded = DraftRun.load(orch.run_id, output_dir=tmp_path)
        assert loaded.calc_result is not None
        assert loaded.calc_result["methodology_id"] == "ACM0022"
        assert len(loaded.calc_result["components"]) == 8

    def test_calc_result_absent_key_loads_as_none(self, tmp_path: Path):
        import json

        run_dir = tmp_path
        run_dir.mkdir(parents=True, exist_ok=True)
        legacy_payload = {
            "run_id": "legacy-no-calc",
            "project_name": "Legacy Project",
            "provider": "noop",
            "sections": [],
            "notes": [],
        }
        (run_dir / "legacy-no-calc.json").write_text(json.dumps(legacy_payload), encoding="utf-8")

        loaded = DraftRun.load("legacy-no-calc", output_dir=run_dir)
        assert loaded.calc_result is None


class TestCalcStructuredContent:
    def _soc_son_calc_result(self):
        import yaml

        from schemas.project_input import ProjectInput
        from pdd_agent.calc.dispatch import compute_for

        root = Path(__file__).parent.parent
        with open(
            root / "configs" / "projects" / "vietnam_socson_from_sheet.yaml", encoding="utf-8"
        ) as f:
            pi = ProjectInput.model_validate(yaml.safe_load(f))
        return compute_for(pi)

    def test_emissions_summary_table_from_annual_schedule(self):
        orch = SectionOrchestrator(provider=NoopProvider())
        orch.set_calc_result(self._soc_son_calc_result())

        result = orch._build_calc_structured_content("4.4")

        assert result["table_type"] == "emissions_summary"
        assert len(result["data"]["entries"]) == 7
        assert result["data"]["entries"][0]["period"] == 1

    def test_monitoring_tracked_params_table_from_calc_result(self):
        orch = SectionOrchestrator(provider=NoopProvider())
        orch.set_calc_result(self._soc_son_calc_result())

        result = orch._build_calc_structured_content("5.2")

        assert result["table_type"] == "monitoring_tracked_params"
        assert len(result["data"]["entries"]) == 4
        assert result["data"]["entries"][0]["parameter"] == "Annual waste throughput"

    def test_non_calc_section_returns_none(self):
        orch = SectionOrchestrator(provider=NoopProvider())
        orch.set_calc_result(self._soc_son_calc_result())

        assert orch._build_calc_structured_content("2.1") is None

    def test_no_calc_result_returns_none(self):
        orch = SectionOrchestrator(provider=NoopProvider())

        assert orch._build_calc_structured_content("4.4") is None


class TestQuantificationSectionScope:
    def test_section_1_subsections_are_quantification_sections(self):
        orch = SectionOrchestrator(provider=NoopProvider())
        assert orch._is_quantification_section("1", "1.10") is True

    def test_section_4_subsections_are_quantification_sections(self):
        orch = SectionOrchestrator(provider=NoopProvider())
        assert orch._is_quantification_section("4", "4.4") is True

    def test_section_3_is_not_a_quantification_section(self):
        orch = SectionOrchestrator(provider=NoopProvider())
        assert orch._is_quantification_section("3", "3.1") is False
