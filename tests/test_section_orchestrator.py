"""Tests for SectionOrchestrator and LLM provider abstraction."""

from __future__ import annotations

import pytest

from pathlib import Path

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
        orch = SectionOrchestrator(run_id="synthetic-review-run")
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
