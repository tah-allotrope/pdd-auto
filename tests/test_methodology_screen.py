"""Tests for methodology screening module."""

from pathlib import Path
from unittest.mock import MagicMock

from pdd_agent.domain.methodology_screen import (
    screen_methodologies,
    MethodologyDatabase,
    _score_technology_match,
    _score_waste_match,
    _score_category_match,
    _score_methodology_id_mentioned,
)
from schemas.project_input import SuggestedMethodology
from pdd_agent.llm.provider import DraftSection


_DATA_DIR = Path(__file__).parent.parent / "data" / "methodologies"


def _mock_project_input(
    technology_type="anaerobic_digestion",
    waste_types=None,
    methodology_ids=None,
):
    pi = MagicMock()
    pi.technology.technology_type = technology_type
    pi.technology.waste_type = waste_types or ["municipal_solid_waste"]
    pi.technology.methodology_ids = methodology_ids or ["ACM0022"]
    return pi


class TestMethodologyDatabase:
    def test_loads_vcs_data(self):
        db = MethodologyDatabase()
        assert len(db._vcs) > 0

    def test_loads_cdm_data(self):
        db = MethodologyDatabase()
        assert len(db._cdm) > 0

    def test_all_methodologies_deduped(self):
        db = MethodologyDatabase()
        all_meths = db.all_methodologies
        ids = [m["id"] for m in all_meths]
        assert len(ids) == len(set(ids))

    def test_data_version(self):
        db = MethodologyDatabase()
        version = db.data_version
        assert "VCS:" in version
        assert "CDM:" in version

    def test_missing_paths_handled(self, tmp_path):
        db = MethodologyDatabase(
            vcs_path=tmp_path / "nonexistent.json",
            cdm_path=tmp_path / "also_nonexistent.json",
        )
        assert db._vcs == []
        assert db._cdm == []


class TestScoringFunctions:
    def test_technology_match_positive(self):
        meth = {"applicable_technology_types": ["anaerobic_digestion", "combined_wte_ad"]}
        assert _score_technology_match(meth, "anaerobic_digestion") == 1.0

    def test_technology_match_negative(self):
        meth = {"applicable_technology_types": ["landfill_gas_capture"]}
        assert _score_technology_match(meth, "anaerobic_digestion") == 0.0

    def test_technology_match_empty(self):
        meth = {"applicable_technology_types": []}
        assert _score_technology_match(meth, "anaerobic_digestion") == 0.0

    def test_waste_match_full(self):
        meth = {"waste_types": ["municipal_solid_waste", "kitchen_waste"]}
        assert _score_waste_match(meth, ["municipal_solid_waste"]) == 1.0

    def test_waste_match_partial(self):
        meth = {"waste_types": ["municipal_solid_waste"]}
        score = _score_waste_match(meth, ["municipal_solid_waste", "industrial_waste"])
        assert 0.0 < score < 1.0

    def test_waste_match_none(self):
        meth = {"waste_types": ["forestry_residue"]}
        assert _score_waste_match(meth, ["municipal_solid_waste"]) == 0.0

    def test_category_match_waste(self):
        meth = {"category": "waste"}
        score = _score_category_match(meth, "a waste to energy project treating landfill waste")
        assert score > 0.0

    def test_category_match_irrelevant(self):
        meth = {"category": "afolu"}
        score = _score_category_match(meth, "a waste to energy project treating landfill waste")
        assert score == 0.0

    def test_methodology_id_mentioned(self):
        meth = {"id": "ACM0022", "name": "Alternative Waste Treatment Processes"}
        score = _score_methodology_id_mentioned(meth, "this project uses acm0022 methodology")
        assert score == 1.0

    def test_methodology_id_not_mentioned(self):
        meth = {"id": "ACM0022", "name": "Alternative Waste Treatment Processes"}
        score = _score_methodology_id_mentioned(meth, "a solar power project")
        assert score == 0.0


class TestScreenMethodologies:
    def test_wte_project_ranks_acm0022_highest(self):
        description = (
            "This project is a waste-to-energy facility that treats municipal solid waste "
            "through anaerobic digestion and thermal treatment. The waste would otherwise "
            "be disposed in a solid waste disposal site (SWDS). The project uses ACM0022 "
            "methodology for alternative waste treatment processes."
        )
        pi = _mock_project_input()
        suggestions = screen_methodologies(description, project_input=pi)
        assert len(suggestions) > 0
        assert suggestions[0].methodology_id == "ACM0022"
        assert suggestions[0].confidence > 0.3

    def test_non_wte_does_not_rank_acm0022_first(self):
        description = (
            "This project captures and destroys landfill gas from an existing "
            "municipal landfill site. The gas is flared using an enclosed ground flare."
        )
        pi = _mock_project_input(
            technology_type="landfill_gas_capture",
            waste_types=["landfill_gas"],
            methodology_ids=["ACM0001"],
        )
        suggestions = screen_methodologies(description, project_input=pi)
        assert len(suggestions) > 0
        assert suggestions[0].methodology_id == "ACM0001"

    def test_confidence_scores_in_range(self):
        suggestions = screen_methodologies("A waste treatment project using anaerobic digestion")
        for s in suggestions:
            assert 0.0 <= s.confidence <= 1.0

    def test_returns_suggested_methodology_instances(self):
        suggestions = screen_methodologies(
            "An organic waste composting project diverting waste from landfill"
        )
        for s in suggestions:
            assert isinstance(s, SuggestedMethodology)
            assert s.methodology_id
            assert s.name
            assert s.rationale

    def test_top_k_limits_results(self):
        suggestions = screen_methodologies("A waste project", top_k=2)
        assert len(suggestions) <= 2

    def test_min_confidence_filters(self):
        suggestions = screen_methodologies(
            "A completely unrelated solar panel installation project",
            min_confidence=0.5,
        )
        for s in suggestions:
            assert s.confidence >= 0.5

    def test_unknown_project_type(self):
        suggestions = screen_methodologies(
            "A novel carbon capture technology using direct air capture with solid sorbents",
        )
        assert isinstance(suggestions, list)

    def test_with_custom_database(self, tmp_path):
        db = MethodologyDatabase(
            vcs_path=tmp_path / "empty.json",
            cdm_path=tmp_path / "empty.json",
        )
        suggestions = screen_methodologies("test project", db=db)
        assert suggestions == []

    def test_rationale_includes_details(self):
        description = (
            "This project uses ACM0022 to treat municipal waste through anaerobic digestion. "
            "Waste is diverted from a solid waste disposal site."
        )
        pi = _mock_project_input()
        suggestions = screen_methodologies(description, project_input=pi)
        top = suggestions[0]
        assert len(top.rationale) > 10

    def test_version_populated(self):
        suggestions = screen_methodologies("A waste treatment project using ACM0022")
        if suggestions:
            assert suggestions[0].version is not None

    def test_active_status_source_populated(self):
        suggestions = screen_methodologies("A waste treatment project")
        if suggestions:
            assert "methodology_db" in suggestions[0].active_status_source

    def test_llm_provider_analyzes_and_reranks_candidates(self):
        provider = MagicMock()
        provider.name = "test-llm"
        provider.draft_section.return_value = DraftSection(
            section_id="methodology_screen",
            sub_section_id="applicability",
            text='[{"methodology_id":"ACM0022","confidence":0.97,"rationale":"All waste-diversion conditions align."}]',
            confidence="HIGH",
            provenance=[],
            issues=[],
            provider="test-llm",
        )
        suggestions = screen_methodologies(
            "ACM0022 waste treatment using anaerobic digestion",
            project_input=_mock_project_input(),
            llm_provider=provider,
        )
        assert suggestions[0].methodology_id == "ACM0022"
        assert suggestions[0].confidence == 0.97
        assert "LLM analysis" in suggestions[0].active_status_source

    def test_invalid_llm_output_falls_back_to_deterministic_results(self):
        provider = MagicMock()
        provider.name = "test-llm"
        provider.draft_section.return_value = DraftSection(
            section_id="methodology_screen",
            sub_section_id="applicability",
            text="not json",
            confidence="LOW",
            provenance=[],
            issues=[],
            provider="test-llm",
        )
        suggestions = screen_methodologies(
            "ACM0022 waste treatment",
            project_input=_mock_project_input(),
            llm_provider=provider,
        )
        assert suggestions
        assert "methodology_db" in suggestions[0].active_status_source
