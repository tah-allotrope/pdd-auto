"""Methodology-parametrized test matrix.

Exercises the draft -> review -> consistency -> export path over all four
methodology families (WTE, rice, biochar, cookstove) using the demo provider,
so the class of bug the rice pilot found by hand fails in CI rather than
in the next live run.
"""

from __future__ import annotations

import pytest

from pdd_agent.agent.section_orchestrator import SectionOrchestrator, family_slug_for
from pdd_agent.llm.provider import DemoProvider, DraftRun
from pdd_agent.review.checks import run_review_checks
from pdd_agent.review.consistency import check_quantitative_consistency
from pdd_agent.review.judge import LLMJudge
from tests.fixtures.methodology_projects import make_project_input

FAMILIES = ["wte", "rice", "biochar", "cookstove"]

_FAMILY_METHOD_IDS = {
    "wte": ["ACM0022"],
    "rice": ["VM0051"],
    "biochar": ["VM0044"],
    "cookstove": ["AMS-II.G"],
}

_FAMILY_TECH_TYPES = {
    "wte": "incineration_with_energy_recovery",
    "rice": "rice_awd",
    "biochar": "biochar_production",
    "cookstove": "improved_cookstoves",
}

_FAMILY_FORBIDDEN_KEYWORDS = {
    "wte": [],
    "rice": ["landfill", "municipal solid waste", "incinerat"],
    "biochar": ["landfill", "municipal solid waste", "rice paddy", "cookstove"],
    "cookstove": ["landfill", "municipal solid waste", "rice paddy", "biochar"],
}


@pytest.mark.parametrize("family", FAMILIES)
class TestFamilyFixtureValidity:
    def test_project_input_validates(self, family):
        project = make_project_input(family)
        assert project.technology.methodology_ids == _FAMILY_METHOD_IDS[family]
        assert project.technology.technology_type == _FAMILY_TECH_TYPES[family]

    def test_family_slug_resolves(self, family):
        project = make_project_input(family)
        assert family_slug_for(project.technology.methodology_ids) == family


@pytest.mark.parametrize("family", FAMILIES)
class TestFamilyDrafting:
    def test_demo_draft_all_sections_non_empty(self, family):
        project = make_project_input(family)
        provider = DemoProvider()
        provider.set_project_input(project)
        orchestrator = SectionOrchestrator(
            provider=provider,
            project_input=project,
        )
        run = orchestrator.run()
        assert isinstance(run, DraftRun)
        assert len(run.sections) > 0
        for section in run.sections:
            assert section.text, f"Section {section.section_id}/{section.sub_section_id} is empty"

    def test_demo_draft_no_cross_family_contamination(self, family):
        project = make_project_input(family)
        provider = DemoProvider()
        provider.set_project_input(project)
        orchestrator = SectionOrchestrator(
            provider=provider,
            project_input=project,
        )
        run = orchestrator.run()
        forbidden = _FAMILY_FORBIDDEN_KEYWORDS.get(family, [])
        all_text = " ".join(s.text for s in run.sections).lower()
        for keyword in forbidden:
            assert keyword.lower() not in all_text, (
                f"Family {family} draft contains cross-family keyword {keyword!r}"
            )


@pytest.mark.parametrize("family", FAMILIES)
class TestFamilyReviewAndConsistency:
    def test_review_checks_run_without_error(self, family):
        project = make_project_input(family)
        provider = DemoProvider()
        provider.set_project_input(project)
        orchestrator = SectionOrchestrator(
            provider=provider,
            project_input=project,
        )
        run = orchestrator.run()
        result = run_review_checks(
            draft_run=run,
            project_input=project,
            run_id=run.run_id,
        )
        assert result is not None

    def test_consistency_check_runs_without_error(self, family):
        project = make_project_input(family)
        provider = DemoProvider()
        provider.set_project_input(project)
        orchestrator = SectionOrchestrator(
            provider=provider,
            project_input=project,
        )
        run = orchestrator.run()
        report = check_quantitative_consistency(
            draft_sections=run.sections,
            project_input=project,
            run_id=run.run_id,
        )
        assert report is not None


@pytest.mark.parametrize("family", FAMILIES)
class TestFamilyJudgeRubricSelection:
    def test_judge_loads_correct_rubric(self, family):
        method_ids = _FAMILY_METHOD_IDS[family]
        judge = LLMJudge(methodology_ids=method_ids)
        rubric_family = judge.rubric.get("family", "wte")
        assert rubric_family == family

    def test_judge_quantitative_sections_from_rubric(self, family):
        method_ids = _FAMILY_METHOD_IDS[family]
        judge = LLMJudge(methodology_ids=method_ids)
        assert isinstance(judge._quantitative_sections, set)
        assert len(judge._quantitative_sections) > 0


class TestJudgeRubricDefaults:
    def test_judge_default_is_wte(self):
        judge = LLMJudge()
        assert judge.rubric.get("family", "wte") == "wte"

    def test_unknown_methodology_falls_back_to_wte(self):
        judge = LLMJudge(methodology_ids=["UNKNOWN-999"])
        assert judge.rubric.get("family", "wte") == "wte"


@pytest.mark.parametrize("family", FAMILIES)
class TestFamilyPromptOverlaySelection:
    def test_orchestrator_selects_correct_overlay(self, family):
        project = make_project_input(family)
        provider = DemoProvider()
        provider.set_project_input(project)
        orchestrator = SectionOrchestrator(
            provider=provider,
            project_input=project,
        )
        assert orchestrator._family_slug() == family
        overlay = orchestrator._load_overlay()
        assert overlay, f"No overlay loaded for family {family}"


class TestPromptOverlayDefaults:
    def test_orchestrator_empty_methodology_defaults_wte(self):
        project = make_project_input("wte")
        project.technology.methodology_ids = []
        provider = DemoProvider()
        orchestrator = SectionOrchestrator(
            provider=provider,
            project_input=project,
        )
        assert orchestrator._family_slug() == "wte"


class TestEdgeCases:
    def test_judge_explicit_rubric_path_overrides_methodology(self, tmp_path):
        import shutil
        from pathlib import Path

        src = Path("rules/verra/rubrics/wte.yaml")
        dst = tmp_path / "custom_rubric.yaml"
        shutil.copy(src, dst)
        judge = LLMJudge(
            rubric_path=dst,
            methodology_ids=["VM0051"],
        )
        assert judge.rubric_path == dst

    def test_biochar_fixture_has_biochar_production_params(self):
        project = make_project_input("biochar")
        assert project.technology.biochar_production is not None
        assert project.technology.biochar_production.dry_mass_tonnes > 0

    def test_cookstove_fixture_has_cookstove_fleet(self):
        project = make_project_input("cookstove")
        assert project.technology.cookstove_fleet is not None
        assert len(project.technology.cookstove_fleet) > 0

    def test_rice_fixture_has_rice_cultivation_params(self):
        project = make_project_input("rice")
        assert project.technology.rice_cultivation is not None
        assert project.technology.rice_cultivation.area_ha > 0
