"""Tests for the VVB-style LLM judge."""

from __future__ import annotations

from types import SimpleNamespace

from pdd_agent.llm.provider import DraftRun, DraftSection
from pdd_agent.review.judge import JudgeResult, LLMJudge


def _project_input():
    return SimpleNamespace(
        quantification=SimpleNamespace(
            net_emissions_tco2e_per_year=75_000.0,
            baseline_emissions_tco2e_per_year=98_000.0,
            project_emissions_tco2e_per_year=21_000.0,
        ),
        evidence_registry=SimpleNamespace(items=[SimpleNamespace(evidence_id="E001")]),
    )


def _section(section_id: str, sub_section_id: str, text: str, **kwargs) -> DraftSection:
    defaults = {
        "confidence": "HIGH",
        "provenance": [],
        "issues": [],
        "provider": "demo",
        "review_sensitivity": "LOW",
        "content_class": "NARRATIVE",
    }
    defaults.update(kwargs)
    return DraftSection(
        section_id=section_id,
        sub_section_id=sub_section_id,
        text=text,
        **defaults,
    )


class TestRubricLoading:
    def test_rubric_loads_with_version_and_criteria(self):
        judge = LLMJudge()
        assert judge.rubric["version"] == "0.1.0"
        assert any(c["id"] == "EVIDENCE_CITATION_VALIDITY" for c in judge.rubric["criteria"])
        assert any(c["id"] == "NO_FABRICATED_FACTS" for c in judge.rubric["criteria"])

    def test_default_pass_threshold_from_rubric(self):
        judge = LLMJudge()
        assert judge.pass_threshold == 70


class TestDeterministicScoring:
    def test_clean_section_passes(self):
        judge = LLMJudge()
        section = _section("1", "1.1", "This is a substantive draft summary for the project.")
        result = judge.judge_section(section)
        assert isinstance(result, JudgeResult)
        assert result.section_key == "1.1"
        assert result.passed is True
        assert result.score >= 70
        assert result.categories["critical"] == []

    def test_invalid_evidence_id_is_critical(self):
        judge = LLMJudge()
        section = _section(
            "3",
            "3.2",
            "Applicability is demonstrated [E999].",
            content_class="METHODOLOGY_DEPENDENT",
        )
        result = judge.judge_section(section, project_input=_project_input())
        assert result.passed is False
        assert any("E999" in msg for msg in result.categories["critical"])

    def test_missing_marker_in_section_3_is_critical(self):
        judge = LLMJudge()
        section = _section(
            "3",
            "3.3",
            "The project boundary is [MISSING] required detail.",
            content_class="METHODOLOGY_DEPENDENT",
        )
        result = judge.judge_section(section)
        assert result.passed is False
        assert any("[MISSING]" in msg for msg in result.categories["critical"])

    def test_missing_marker_in_section_1_is_advisory(self):
        judge = LLMJudge()
        section = _section("1", "1.1", "Summary [MISSING] data.")
        result = judge.judge_section(section)
        assert not result.categories["critical"]
        assert any("[MISSING]" in msg for msg in result.categories["advisory"])

    def test_calc_contradiction_is_critical(self):
        judge = LLMJudge()
        section = _section(
            "4",
            "4.4",
            "The net GHG emission reductions are 12,345 tCO2e/year.",
            content_class="QUANTITATIVE",
        )
        result = judge.judge_section(section, project_input=_project_input())
        assert result.passed is False
        assert any("12,345" in msg for msg in result.categories["critical"])

    def test_calc_match_passes(self):
        judge = LLMJudge()
        section = _section(
            "4",
            "4.4",
            "The net GHG emission reductions are 75,000 tCO2e/year.",
            content_class="QUANTITATIVE",
        )
        result = judge.judge_section(section, project_input=_project_input())
        assert result.passed is True
        assert result.categories["critical"] == []

    def test_completeness_advisory_lowers_score(self):
        judge = LLMJudge()
        section = _section("1", "1.1", "")
        result = judge.judge_section(section)
        assert not result.categories["critical"]
        assert any("short" in msg for msg in result.categories["advisory"])


class TestJudgeRun:
    def test_judge_run_scores_all_sections(self):
        judge = LLMJudge()
        run = DraftRun(run_id="judge-test", project_name="Test")
        run.add(_section("1", "1.1", "Summary text."))
        run.add(_section("4", "4.4", "Net reductions are 75,000 tCO2e/year."))
        results = judge.judge_run(run, project_input=_project_input())
        assert len(results) == 2
        assert "1.1" in results
        assert "4.4" in results

    def test_judge_run_from_dict(self):
        judge = LLMJudge()
        run_data = {
            "run_id": "judge-dict-test",
            "project_name": "Test",
            "provider": "noop",
            "sections": [
                {
                    "section_id": "3",
                    "sub_section_id": "3.3",
                    "text": "Boundary [MISSING].",
                    "confidence": "HIGH",
                    "provenance": [],
                    "issues": [],
                    "provider": "noop",
                    "review_sensitivity": "HIGH",
                    "content_class": "METHODOLOGY_DEPENDENT",
                }
            ],
            "notes": [],
        }
        results = judge.judge_run(run_data)
        assert "3.3" in results
        assert results["3.3"].passed is False
        assert any("[MISSING]" in msg for msg in results["3.3"].categories["critical"])


class TestJudgeInterface:
    def test_judge_result_to_dict_shape(self):
        judge = LLMJudge()
        section = _section("1", "1.1", "Clean draft.")
        result = judge.judge_section(section)
        d = result.to_dict()
        assert set(d.keys()) >= {"section_key", "score", "passed", "categories", "findings"}
        assert "critical" in d["categories"]
        assert "advisory" in d["categories"]

    def test_llm_judge_interface_keeps_provider_name(self):
        judge = LLMJudge(provider_name="openai")
        assert judge.provider_name == "openai"
        # Default use_llm=False falls back to deterministic scoring.
        section = _section("1", "1.1", "Clean draft.")
        result = judge.judge_section(section)
        assert result.passed is True


class TestParseJudgeJson:
    def test_parses_clean_json(self):
        from pdd_agent.review.judge import _parse_judge_json

        text = '{"score": 82, "passed": true, "critical": [], "advisory": ["cite E002"]}'
        payload = _parse_judge_json(text)
        assert payload == {"score": 82, "passed": True, "critical": [], "advisory": ["cite E002"]}

    def test_parses_json_wrapped_in_markdown_fence(self):
        from pdd_agent.review.judge import _parse_judge_json

        text = (
            "Here you go:\n```json\n"
            '{"score": 82, "passed": true, "critical": [], "advisory": ["cite E002"]}\n'
            "```"
        )
        payload = _parse_judge_json(text)
        assert payload["score"] == 82
        assert payload["advisory"] == ["cite E002"]

    def test_no_json_returns_none(self):
        from pdd_agent.review.judge import _parse_judge_json

        assert _parse_judge_json("no json here, score: 75") is None

    def test_empty_text_returns_none(self):
        from pdd_agent.review.judge import _parse_judge_json

        assert _parse_judge_json("") is None

    def test_json_without_score_key_returns_none(self):
        from pdd_agent.review.judge import _parse_judge_json

        assert _parse_judge_json('{"foo": "bar"}') is None


class TestJudgeModelTier:
    def test_explicit_model_name_wins(self, monkeypatch):
        monkeypatch.delenv("PDD_JUDGE_MODEL", raising=False)
        judge = LLMJudge(provider_name="anthropic", model_name="claude-opus-4-8")
        assert judge.model_name == "claude-opus-4-8"

    def test_env_override_used_when_no_explicit_model(self, monkeypatch):
        monkeypatch.setenv("PDD_JUDGE_MODEL", "claude-haiku-4-5-20251001")
        judge = LLMJudge(provider_name="anthropic")
        assert judge.model_name == "claude-haiku-4-5-20251001"

    def test_tier_default_for_anthropic(self, monkeypatch):
        monkeypatch.delenv("PDD_JUDGE_MODEL", raising=False)
        judge = LLMJudge(provider_name="anthropic")
        assert judge.model_name == "claude-haiku-4-5-20251001"

    def test_tier_default_for_openai(self, monkeypatch):
        monkeypatch.delenv("PDD_JUDGE_MODEL", raising=False)
        judge = LLMJudge(provider_name="openai")
        assert judge.model_name == "gpt-4o-mini"

    def test_no_tier_default_for_demo(self, monkeypatch):
        monkeypatch.delenv("PDD_JUDGE_MODEL", raising=False)
        judge = LLMJudge(provider_name="demo")
        assert judge.model_name is None


class TestLlmJudgeStructuredFindings:
    def test_llm_judge_section_populates_categories_from_json(self):
        judge = LLMJudge(provider_name="demo", use_llm=True)
        judge.provider_name = "openai"  # bypass the demo/noop use_llm guard

        class _FakeProvider:
            def draft_section(self, **kwargs):
                from pdd_agent.llm.provider import DraftSection

                return DraftSection(
                    section_id="judge",
                    sub_section_id=kwargs["sub_section_id"],
                    text='{"score": 40, "passed": false, "critical": ["fabricated number"], "advisory": []}',
                    confidence="HIGH",
                    provenance=[],
                    issues=[],
                    provider="openai",
                )

        judge._provider = _FakeProvider()
        section = _section("4", "4.1", "Baseline emissions: 999999 tCO2e.")

        result = judge._llm_judge_section(section, None, None)

        assert result.score == 40
        assert result.passed is False
        assert result.categories["critical"] == ["fabricated number"]
        assert len(result.findings) == 1
        assert result.findings[0]["category"] == "critical"

    def test_llm_judge_section_falls_back_on_unparseable_response(self):
        judge = LLMJudge(provider_name="demo", use_llm=True)
        judge.provider_name = "openai"

        class _FakeProvider:
            def draft_section(self, **kwargs):
                from pdd_agent.llm.provider import DraftSection

                return DraftSection(
                    section_id="judge",
                    sub_section_id=kwargs["sub_section_id"],
                    text="I cannot evaluate this section.",
                    confidence="HIGH",
                    provenance=[],
                    issues=[],
                    provider="openai",
                )

        judge._provider = _FakeProvider()
        section = _section("1", "1.1", "Clean draft.")

        result = judge._llm_judge_section(section, None, None)
        deterministic = judge._deterministic_judge_section(section, None, None)

        assert result.score == deterministic.score
        assert result.passed == deterministic.passed
