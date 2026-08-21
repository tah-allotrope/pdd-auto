"""Tests for per-section character budgets and honest truncation (S-2)."""

from __future__ import annotations

from pathlib import Path

import yaml

from pdd_agent.agent.section_orchestrator import SectionOrchestrator
from pdd_agent.llm.provider import DraftSection
from schemas.project_input import ProjectInput

_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "pdd_section_schema.yaml"


class _FixedLengthProvider:
    name = "fixed-length"

    def __init__(self, text: str, confidence: str = "HIGH"):
        self._text = text
        self._confidence = confidence
        self.seen_max_chars: list[int] = []

    def draft_section(self, section_id, sub_section_id, prompt, provenance, max_chars=4000):
        self.seen_max_chars.append(max_chars)
        return DraftSection(
            section_id=section_id,
            sub_section_id=sub_section_id,
            text=self._text,
            confidence=self._confidence,
            provenance=list(provenance),
            issues=[],
            provider=self.name,
        )

    def close(self):
        pass


def _all_subsections() -> list[dict]:
    data = yaml.safe_load(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return [ss for s in data["sections"] for ss in s.get("sub_sections", [])]


class TestBudgetResolution:
    def test_quantitative_budget(self):
        orch = SectionOrchestrator()
        assert orch.section_budget_chars("4", "4.4") == 20000

    def test_factual_budget(self):
        orch = SectionOrchestrator()
        assert orch.section_budget_chars("1", "1.2") == 3000

    def test_optional_budget(self):
        orch = SectionOrchestrator()
        assert orch.section_budget_chars("1", "1.18") == 2000

    def test_methodology_dependent_budget(self):
        orch = SectionOrchestrator()
        assert orch.section_budget_chars("3", "3.5") == 12000

    def test_unknown_subsection_defaults_to_4000(self):
        orch = SectionOrchestrator()
        assert orch.section_budget_chars("9", "9.9") == 4000

    def _project_with_ceiling(self, ceiling: int) -> ProjectInput:
        data = yaml.safe_load(
            (
                Path(__file__).parent.parent / "configs" / "projects" / "demo_socson_like.yaml"
            ).read_text(encoding="utf-8")
        )
        data["generation_controls"] = {"max_tokens_per_section": ceiling}
        return ProjectInput.model_validate(data)

    def test_global_ceiling_caps_schema_budget(self):
        orch = SectionOrchestrator(project_input=self._project_with_ceiling(5000))
        assert orch.section_budget_chars("4", "4.4") == 5000

    def test_schema_budget_binds_when_ceiling_high(self):
        orch = SectionOrchestrator(project_input=self._project_with_ceiling(40000))
        assert orch.section_budget_chars("4", "4.4") == 20000

    def test_sum_over_all_subsections_is_297000(self):
        orch = SectionOrchestrator()
        subs = _all_subsections()
        total = sum(
            orch.section_budget_chars(sub["sub_section_id"].split(".")[0], sub["sub_section_id"])
            for sub in subs
        )
        assert total == 297000


class TestSchemaBudgetKeys:
    def test_every_subsection_has_max_chars_in_range(self):
        subs = _all_subsections()
        assert len(subs) == 36
        for ss in subs:
            assert "max_chars" in ss, ss["sub_section_id"]
            assert isinstance(ss["max_chars"], int)
            assert 2000 <= ss["max_chars"] <= 20000


class TestTruncationReporting:
    def test_long_output_truncated_with_issue_and_downgrade(self):
        provider = _FixedLengthProvider("x" * 25000, confidence="HIGH")
        orch = SectionOrchestrator(provider=provider)
        draft = orch.draft_section("4", "4.4")
        assert len(draft.text) == 20000
        truncated = [i for i in draft.issues if i.startswith("TRUNCATED: ")]
        assert len(truncated) == 1
        assert "25000" in truncated[0]
        assert "20000" in truncated[0]
        assert draft.confidence == "MEDIUM"

    def test_low_confidence_stays_low_when_truncated(self):
        provider = _FixedLengthProvider("x" * 25000, confidence="LOW")
        orch = SectionOrchestrator(provider=provider)
        draft = orch.draft_section("4", "4.4")
        assert len(draft.text) == 20000
        assert draft.confidence == "LOW"

    def test_short_output_untouched(self):
        provider = _FixedLengthProvider("short text", confidence="HIGH")
        orch = SectionOrchestrator(provider=provider)
        draft = orch.draft_section("4", "4.4")
        assert draft.text == "short text"
        assert not any(i.startswith("TRUNCATED: ") for i in draft.issues)
        assert draft.confidence == "HIGH"

    def test_provider_receives_resolved_budget(self):
        provider = _FixedLengthProvider("short text")
        orch = SectionOrchestrator(provider=provider)
        orch.draft_section("4", "4.4")
        assert provider.seen_max_chars == [20000]
