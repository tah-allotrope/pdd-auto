"""Tests for v2 prompt assembly, calc injection, and enhanced retrieval wiring."""

import json
import urllib.request
from unittest.mock import MagicMock, patch
from pathlib import Path

from pdd_agent.agent.section_orchestrator import SectionOrchestrator, system_prompt_for
from pdd_agent.llm.provider import NoopProvider, DemoProvider, ModelConfig
from pdd_agent.llm.budget import TokenBudget


def _mock_project_input(methodology_ids=None, technology_type=None):
    """Build a minimal mock ProjectInput for testing."""
    proj = MagicMock()
    proj.project.project_name = "Test WTE Project"
    proj.location.city = "TestCity"
    proj.location.country = "TestCountry"
    proj.technology.methodology_ids = methodology_ids or ["ACM0022"]
    proj.technology.technology_type = technology_type or "anaerobic_digestion"
    proj.technology.installed_capacity_mw = 5.0
    proj.technology.annual_waste_throughput = 100000
    proj.quantification.net_emissions_tco2e_per_year = 50000
    proj.dates.crediting_period_years = 10
    proj.generation_controls = None
    proj.review_flags = None
    proj.evidence_registry = None
    return proj


def _mock_calc_result():
    """Build a mock ACM0022CalcResult."""
    cr = MagicMock()
    cr.baseline_emissions_tco2e = 80000.0
    cr.baseline_methane_swds_tco2e = 65000.0
    cr.baseline_electricity_tco2e = 15000.0
    cr.project_emissions_tco2e = 20000.0
    cr.project_electricity_consumption_tco2e = 5000.0
    cr.project_fossil_fuel_tco2e = 3000.0
    cr.project_methane_leakage_tco2e = 8000.0
    cr.project_flaring_tco2e = 4000.0
    cr.leakage_tco2e = 10000.0
    cr.leakage_rdf_combustion_tco2e = 9000.0
    cr.leakage_digestate_tco2e = 1000.0
    cr.net_emission_reductions_tco2e = 50000.0
    cr.crediting_period_total_tco2e = 350000.0
    cr.crediting_period_years = 7
    cr.organic_waste_to_ad_tonnes = 60000.0
    cr.annual_biogas_m3 = 7800000.0
    cr.annual_methane_m3 = 4368000.0
    cr.annual_methane_tonnes = 2920.0
    cr.electricity_generated_mwh = 17800.0
    cr.methodology_version = "ACM0022 v3.0"
    return cr


def _mock_retrieval_result(
    doc_name="TestDoc", heading="Test Heading", text="Example text", score=5.0
):
    result = MagicMock()
    result.document_name = doc_name
    result.canonical_heading = heading
    result.text = text
    result.score = score
    result.content_class = "NARRATIVE"
    return result


_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "pdd_section_schema.yaml"
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class TestV2PromptAssembly:
    def test_v2_prompt_includes_authority_order(self):
        project = _mock_project_input()
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        orch._use_v2_prompt = True
        examples = [_mock_retrieval_result()]
        prompt = orch._build_prompt("1", "1.1", examples, project)
        assert "Authority Order" in prompt
        assert "Input YAML > Evidence" in prompt

    def test_v2_prompt_includes_anti_hallucination(self):
        project = _mock_project_input()
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        orch._use_v2_prompt = True
        examples = [_mock_retrieval_result()]
        prompt = orch._build_prompt("1", "1.1", examples, project)
        assert "[MISSING]" in prompt
        assert "[INFERENCE]" in prompt
        assert "[REVIEW REQUIRED]" in prompt

    def test_v1_prompt_no_authority_order(self):
        project = _mock_project_input()
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        orch._use_v2_prompt = False
        examples = [_mock_retrieval_result()]
        prompt = orch._build_prompt("1", "1.1", examples, project)
        assert "Authority Order" not in prompt

    def test_demo_uses_v1_prompt(self):
        project = _mock_project_input()
        orch = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        assert orch._use_v2_prompt is False


class TestCalcInjection:
    def test_calc_injection_in_section_4(self):
        project = _mock_project_input()
        calc = _mock_calc_result()
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
            calc_result=calc,
        )
        orch._use_v2_prompt = True
        examples = [_mock_retrieval_result()]
        prompt = orch._build_prompt("4", "4.1", examples, project)
        assert "ACM0022 Calculation Engine Results" in prompt
        assert "[CALC: baseline_total]" in prompt
        assert "80,000.00" in prompt
        assert "[CALC: net_ER]" in prompt

    def test_calc_injection_in_section_1(self):
        """S-3: injection scope was widened from Section 4 only to Sections 1 and 4
        in PHASE-05 of the calc-correctness-and-audit-trail plan."""
        project = _mock_project_input()
        calc = _mock_calc_result()
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
            calc_result=calc,
        )
        orch._use_v2_prompt = True
        examples = [_mock_retrieval_result()]
        prompt = orch._build_prompt("1", "1.1", examples, project)
        assert "ACM0022 Calculation Engine Results" in prompt

    def test_no_calc_injection_without_result(self):
        project = _mock_project_input()
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        orch._use_v2_prompt = True
        examples = [_mock_retrieval_result()]
        prompt = orch._build_prompt("4", "4.1", examples, project)
        assert "ACM0022 Calculation Engine Results" not in prompt

    def test_calc_intermediates_included(self):
        project = _mock_project_input()
        calc = _mock_calc_result()
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
            calc_result=calc,
        )
        text = orch._format_calc_injection()
        assert "Organic waste to AD" in text
        assert "Annual biogas" in text
        assert "MWh/year" in text

    def test_calc_injection_header_names_resolved_methodology(self):
        project = _mock_project_input(methodology_ids=["VM0051"])
        calc = _mock_calc_result()
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
            calc_result=calc,
        )
        text = orch._format_calc_injection()
        assert "VM0051 Calculation Engine Results" in text
        assert "ACM0022 Calculation Engine Results" not in text

    def test_calc_injection_header_defaults_to_acm0022_without_project(self):
        calc = _mock_calc_result()
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=None,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
            calc_result=calc,
        )
        text = orch._format_calc_injection()
        assert "ACM0022 Calculation Engine Results" in text


class TestMethodologyOverlay:
    def test_wte_project_resolves_wte_family(self):
        project = _mock_project_input(methodology_ids=["ACM0022"])
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        assert orch._family_slug() == "wte"

    def test_rice_project_resolves_rice_family(self):
        project = _mock_project_input(methodology_ids=["VM0051"], technology_type="rice_awd")
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        assert orch._family_slug() == "rice"

    def test_biochar_project_resolves_biochar_family(self):
        project = _mock_project_input(
            methodology_ids=["VM0044"], technology_type="biochar_production"
        )
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        assert orch._family_slug() == "biochar"

    def test_cookstove_project_resolves_cookstove_family(self):
        project = _mock_project_input(
            methodology_ids=["AMS-II.G"], technology_type="improved_cookstoves"
        )
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        assert orch._family_slug() == "cookstove"

    def test_unknown_methodology_falls_back_to_wte(self):
        project = _mock_project_input(methodology_ids=["UNKNOWN-METH"])
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        assert orch._family_slug() == "wte"

    def test_empty_methodology_ids_falls_back_to_wte(self):
        project = _mock_project_input(methodology_ids=[])
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        assert orch._family_slug() == "wte"

    def test_no_project_input_falls_back_to_wte(self):
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=None,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        assert orch._family_slug() == "wte"

    def test_wte_prompt_contains_wte_overlay(self):
        project = _mock_project_input(methodology_ids=["ACM0022"])
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        orch._use_v2_prompt = True
        examples = [_mock_retrieval_result()]
        prompt = orch._build_prompt("1", "1.1", examples, project)
        assert "waste-to-energy" in prompt.lower()

    def test_rice_prompt_contains_rice_overlay_not_wte_keywords(self):
        project = _mock_project_input(methodology_ids=["VM0051"], technology_type="rice_awd")
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        orch._use_v2_prompt = True
        examples = [_mock_retrieval_result()]
        prompt = orch._build_prompt("1", "1.1", examples, project)
        assert "vm0051" in prompt.lower()
        assert "alternate wetting and drying" in prompt.lower() or "awd" in prompt.lower()
        assert "landfill" not in prompt.lower()
        assert "municipal solid waste" not in prompt.lower()

    def test_biochar_prompt_contains_biochar_overlay(self):
        project = _mock_project_input(
            methodology_ids=["VM0044"], technology_type="biochar_production"
        )
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        orch._use_v2_prompt = True
        examples = [_mock_retrieval_result()]
        prompt = orch._build_prompt("1", "1.1", examples, project)
        assert "biochar" in prompt.lower()
        assert "pyrolysis" in prompt.lower()

    def test_cookstove_prompt_contains_cookstove_overlay(self):
        project = _mock_project_input(
            methodology_ids=["AMS-II.G"], technology_type="improved_cookstoves"
        )
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        orch._use_v2_prompt = True
        examples = [_mock_retrieval_result()]
        prompt = orch._build_prompt("1", "1.1", examples, project)
        assert "cookstove" in prompt.lower()

    def test_missing_family_overlay_falls_back_to_wte(self, tmp_path):
        methodologies_dir = tmp_path / "methodologies"
        methodologies_dir.mkdir(parents=True)
        (methodologies_dir / "wte.md").write_text(
            "## Domain & Methodology Context\n\nFallback waste-to-energy overlay.\n",
            encoding="utf-8",
        )
        # No rice.md written — simulates an incomplete overlay set.
        project = _mock_project_input(methodology_ids=["VM0051"], technology_type="rice_awd")
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=tmp_path,
        )
        overlay = orch._load_overlay()
        assert "Fallback waste-to-energy overlay" in overlay

    def test_v1_prompt_does_not_inject_overlay(self):
        """The overlay is only injected for the v2 prompt path (demo/noop use v1)."""
        project = _mock_project_input(methodology_ids=["VM0051"], technology_type="rice_awd")
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        orch._use_v2_prompt = False
        examples = [_mock_retrieval_result()]
        prompt = orch._build_prompt("1", "1.1", examples, project)
        assert "Domain & Methodology Context" not in prompt


class TestEnhancedRetrieval:
    def test_retrieval_format_with_scores(self):
        project = _mock_project_input()
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        examples = [
            _mock_retrieval_result("Doc1", "Heading1", "Text1", 7.5),
            _mock_retrieval_result("Doc2", "Heading2", "Text2", 3.2),
        ]
        result = orch._format_retrieval_results(examples, max_examples=5, max_chars=1500)
        assert "FTS5/BM25 retrieval" in result
        assert "BM25 score: 7.500" in result
        assert "Doc1" in result
        assert "Doc2" in result

    def test_retrieval_format_empty(self):
        project = _mock_project_input()
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        result = orch._format_retrieval_results([], max_examples=5, max_chars=1500)
        assert "NONE" in result

    def test_retrieval_respects_max_chars(self):
        project = _mock_project_input()
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        examples = [_mock_retrieval_result(text="x" * 5000)]
        result = orch._format_retrieval_results(examples, max_examples=5, max_chars=100)
        assert "x" * 101 not in result


class TestBudgetIntegration:
    @patch("pdd_agent.agent.section_orchestrator.get_examples_for_section", return_value=[])
    def test_budget_exhaustion_stops_drafting(self, _mock_ex):
        project = _mock_project_input()
        budget = TokenBudget(max_tokens=100)
        budget.record("0.0", input_tokens=80, output_tokens=30)

        orch = SectionOrchestrator(
            provider=NoopProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
            token_budget=budget,
        )

        result = orch.draft_section("1", "1.1")
        assert result.confidence == "UNSUPPORTED"
        assert "BUDGET EXHAUSTED" in result.text

    @patch("pdd_agent.agent.section_orchestrator.get_examples_for_section", return_value=[])
    def test_budget_summary_in_run_notes(self, _mock_ex):
        project = _mock_project_input()
        budget = TokenBudget(max_tokens=500000)

        orch = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=project,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
            token_budget=budget,
        )

        run = orch.run()
        assert any("token_budget" in note for note in run.notes)


class TestSchemaExtensions:
    def test_generation_controls_import(self):
        from schemas.project_input import GenerationControls

        gc = GenerationControls()
        assert gc.provider_name == "noop"
        assert gc.token_budget == 500_000
        assert gc.use_v2_prompt is True

    def test_review_flags_import(self):
        from schemas.project_input import ReviewFlags

        rf = ReviewFlags()
        assert rf.require_evidence_for_high is True
        assert rf.block_on_missing_markers is True

    def test_evidence_registry_import(self):
        from schemas.project_input import EvidenceRegistry

        reg = EvidenceRegistry()
        eid = reg.add("corpus", "Test evidence", section_ref="1.1")
        assert eid == "E001"
        assert len(reg.items) == 1
        assert reg.items[0].evidence_id == "E001"
        assert reg.by_section("1.1") == [reg.items[0]]
        assert reg.by_section("2.1") == []

    def test_project_input_with_optional_extensions(self):
        from schemas.project_input import ProjectInput

        data = _minimal_project_dict()
        pi = ProjectInput(**data)
        assert pi.generation_controls is None
        assert pi.review_flags is None
        assert pi.evidence_registry is None

    def test_project_input_with_generation_controls(self):
        from schemas.project_input import ProjectInput

        data = _minimal_project_dict()
        data["generation_controls"] = {"provider_name": "openai", "model_name": "gpt-4o"}
        pi = ProjectInput(**data)
        assert pi.generation_controls is not None
        assert pi.generation_controls.provider_name == "openai"


def _minimal_project_dict():
    return {
        "project": {
            "project_name": "Test Project",
            "proponent_name": "Test Corp",
            "proponent_contact_email": "test@test.com",
            "ownership": "Test Corp owns 100%",
        },
        "location": {
            "country": "Turkey",
            "region": "Bursa",
            "city": "Inegol",
            "latitude": 40.08,
            "longitude": 29.51,
        },
        "dates": {
            "start_date": "2024-01-01",
            "crediting_period_start": "2024-06-01",
            "crediting_period_years": 10,
        },
        "technology": {
            "methodology_ids": ["ACM0022"],
            "technology_type": "anaerobic_digestion",
            "waste_type": ["municipal_solid_waste"],
            "annual_waste_throughput": 100000,
            "installed_capacity_mw": 5.0,
        },
        "methodology_applicability": {
            "eligibility_checklist": {"AC-01": True, "AC-02": True},
        },
        "quantification": {},
        "monitoring": {
            "parameters_monitored": [
                {
                    "name": "waste",
                    "unit": "t/yr",
                    "frequency": "continuous",
                    "method": "weighbridge",
                    "data_source": "project",
                }
            ],
            "data_management": "Digital records",
        },
        "safeguards": {
            "no_net_harm_statement": "No net harm confirmed",
        },
        "compliance_and_ownership": {
            "credit_ownership_statement": "Test Corp owns all credits",
        },
        "sustainable_development": {},
    }


class TestSystemPromptFor:
    """PHASE-03: family-aware system prompt shared by the three real providers."""

    _WTE_GOLDEN = (
        "You are a technical writing assistant specializing in Verra VCS "
        "carbon credit Project Design Documents for waste-to-energy projects. "
        "Follow the prompt instructions exactly. Cite all sources using the "
        "required citation format. Never fabricate data."
    )

    def test_wte_is_byte_identical_to_prior_hardcoded_constant(self):
        assert system_prompt_for(["ACM0022"]) == self._WTE_GOLDEN

    def test_rice_contains_descriptor_and_not_wte(self):
        prompt = system_prompt_for(["VM0051"])
        assert "rice cultivation (alternate wetting and drying) projects" in prompt
        assert "waste-to-energy" not in prompt

    def test_biochar_and_cookstove_descriptors(self):
        assert "biochar carbon-removal projects" in system_prompt_for(["VM0044"])
        assert "improved cookstove projects" in system_prompt_for(["AMS-II.G"])

    def test_none_empty_and_unknown_default_to_wte(self):
        assert system_prompt_for(None) == self._WTE_GOLDEN
        assert system_prompt_for([]) == self._WTE_GOLDEN
        assert system_prompt_for(["UNKNOWN"]) == self._WTE_GOLDEN


class TestOllamaProviderSystemPromptHook:
    def test_default_then_custom_system_prompt(self):
        from pdd_agent.llm.ollama_provider import OllamaProvider, _DEFAULT_SYSTEM_PROMPT

        provider = OllamaProvider(ModelConfig(provider_name="ollama", model_name="m"))
        captured = {}

        class _FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps({"message": {"content": "ok"}}).encode("utf-8")

        def fake_urlopen(request, timeout=None):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return _FakeResponse()

        with patch.object(urllib.request, "urlopen", side_effect=fake_urlopen):
            provider.draft_section("1", "1.1", "p", [])
            assert captured["body"]["messages"][0]["content"] == _DEFAULT_SYSTEM_PROMPT

            provider.set_system_prompt("CUSTOM")
            provider.draft_section("1", "1.1", "p", [])
            assert captured["body"]["messages"][0]["content"] == "CUSTOM"


class TestOrchestratorSystemPromptWiring:
    def test_orchestrator_pushes_family_system_prompt_to_provider(self):
        from tests.fixtures.methodology_projects import make_project_input

        provider = MagicMock()
        provider.name = "stub"
        project = make_project_input("rice")

        SectionOrchestrator(
            provider=provider,
            project_input=project,
            token_budget=TokenBudget(),
        )

        provider.set_system_prompt.assert_called_once()
        call_arg = provider.set_system_prompt.call_args[0][0]
        assert "rice cultivation" in call_arg
