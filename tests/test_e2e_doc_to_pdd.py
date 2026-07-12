"""Integration test: document -> extraction -> screening -> draft E2E.

Tests the full pipeline from a raw project description through extraction,
methodology screening, and PDD drafting using DemoProvider for deterministic output.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from pdd_agent.ingest.extract import extract_project_input, ExtractionError
from pdd_agent.domain.methodology_screen import screen_methodologies
from pdd_agent.agent.section_orchestrator import SectionOrchestrator
from pdd_agent.llm.provider import DraftSection, NoopProvider, DemoProvider
from schemas.project_input import ProjectInput, SuggestedMethodology


_SCHEMA_PATH = Path("schemas/pdd_section_schema.yaml")
_PROMPTS_DIR = Path("prompts")

_INEGOL_DESCRIPTION = """\
Project Name: İnegöl Integrated Solid Waste Management and Energy Production Project
Project ID: VCS-3908
Proponent: BIOTREND ENERJI A.Ş.
Contact: info@biotrend.com.tr

Location: İnegöl district, Bursa Province, Türkiye
GPS: 40.08°N, 29.51°E

Technology: Combined waste-to-energy facility with anaerobic digestion and thermal treatment.
The project treats municipal solid waste that would otherwise be disposed in a solid waste
disposal site (SWDS). The facility has an installed capacity of 8.484 MW and processes
approximately 262,970 tonnes of waste per year.

Methodology: ACM0022 — Alternative Waste Treatment Processes (v3.0)

The project uses anaerobic digestion to process organic fraction of municipal solid waste,
producing biogas for electricity generation. Refuse-derived fuel (RDF) is produced from
non-biodegradable fractions. The project diverts waste from the Inegol landfill site.

Crediting Period: 7 years starting from 2021-06-01
Project Start Date: 2020-12-31

Ownership: MUNDO VERDE GmbH is the sole credit owner.

Applicability Conditions:
- AC-01: Waste treated would have been disposed in SWDS — Yes
- AC-02: Project uses alternative waste treatment — Yes
- AC-03: Not exclusively biomass from agriculture — Yes

Monitoring:
- Waste throughput measured by weighbridge (continuous)
- Biogas flow and CH4 concentration measured continuously
- Electricity generation metered at grid connection

Sustainable Development:
- SDG-7: Affordable and Clean Energy
- SDG-13: Climate Action
- SDG-11: Sustainable Cities
"""


def _mock_extraction_provider(yaml_text: str):
    """Create a mock provider that returns the given YAML text for extraction."""
    provider = MagicMock()
    provider.name = "mock"
    provider.draft_section.return_value = DraftSection(
        section_id="extract",
        sub_section_id="project_input",
        text=yaml_text,
        confidence="HIGH",
        provenance=["[EXTRACTION: document intake]"],
        issues=[],
        provider="mock",
    )
    return provider


_MOCK_EXTRACTION_YAML = """\
project:
  project_name: "İnegöl Integrated Solid Waste Management and Energy Production Project"
  project_id_vcs: "VCS-3908"
  proponent_name: "BIOTREND ENERJI A.Ş."
  proponent_contact_email: "info@biotrend.com.tr"
  other_entities: ["MUNDO VERDE GmbH"]
  ownership: "MUNDO VERDE GmbH is the sole credit owner"
  prepared_by: null
location:
  country: "Turkey"
  region: "Bursa"
  city: "İnegöl"
  latitude: 40.08
  longitude: 29.51
dates:
  start_date: "2020-12-31"
  crediting_period_start: "2021-06-01"
  crediting_period_years: 7
technology:
  methodology_ids: ["ACM0022"]
  technology_type: "combined_wte_ad"
  waste_type: ["municipal_solid_waste"]
  annual_waste_throughput: 262970
  installed_capacity_mw: 8.484
methodology_applicability:
  eligibility_checklist:
    AC-01: true
    AC-02: true
    AC-03: true
quantification:
  baseline_emissions_tco2e_per_year: null
  project_emissions_tco2e_per_year: null
  leakage_tco2e_per_year: null
  net_emissions_tco2e_per_year: null
monitoring:
  parameters_monitored:
    - name: "waste throughput"
      unit: "t/yr"
      frequency: "continuous"
      method: "weighbridge"
      data_source: "project"
    - name: "biogas flow"
      unit: "m3/hr"
      frequency: "continuous"
      method: "flow meter"
      data_source: "project"
    - name: "electricity generation"
      unit: "MWh"
      frequency: "continuous"
      method: "grid meter"
      data_source: "project"
  data_management: "Digital records and SCADA system"
safeguards:
  no_net_harm_statement: "No net harm analysis completed"
compliance_and_ownership:
  credit_ownership_statement: "MUNDO VERDE GmbH is the sole credit owner"
sustainable_development:
  sd_contributions: ["SDG-7", "SDG-13", "SDG-11"]
_extraction:
  extracted_fields: ["project.project_name", "location.country", "technology.methodology_ids", "technology.annual_waste_throughput"]
  defaulted_fields: ["quantification"]
  missing_fields: []
  confidence_notes: "High quality extraction from structured project description"
"""


class TestDocToExtractionE2E:
    def test_extraction_from_text_produces_valid_input(self):
        provider = _mock_extraction_provider(_MOCK_EXTRACTION_YAML)
        result = extract_project_input(_INEGOL_DESCRIPTION, provider)
        assert isinstance(result, ProjectInput)
        assert "neg" in result.project.project_name.lower() and "Waste" in result.project.project_name
        assert result.technology.methodology_ids == ["ACM0022"]
        assert result.technology.annual_waste_throughput == 262970

    def test_extraction_from_file(self, tmp_path):
        doc = tmp_path / "inegol_description.txt"
        doc.write_text(_INEGOL_DESCRIPTION, encoding="utf-8")
        provider = _mock_extraction_provider(_MOCK_EXTRACTION_YAML)
        result = extract_project_input(doc, provider)
        assert result.extraction_provenance is not None
        assert result.extraction_provenance.source_document == str(doc)

    def test_extraction_provenance_tracks_fields(self):
        provider = _mock_extraction_provider(_MOCK_EXTRACTION_YAML)
        result = extract_project_input(_INEGOL_DESCRIPTION, provider)
        prov = result.extraction_provenance
        assert prov is not None
        assert "project.project_name" in prov.extracted_fields
        assert len(prov.missing_fields) == 0


class TestScreeningE2E:
    def test_wte_description_ranks_acm0022_first(self):
        suggestions = screen_methodologies(_INEGOL_DESCRIPTION)
        assert len(suggestions) > 0
        assert suggestions[0].methodology_id == "ACM0022"

    def test_screening_with_extracted_input(self):
        provider = _mock_extraction_provider(_MOCK_EXTRACTION_YAML)
        pi = extract_project_input(_INEGOL_DESCRIPTION, provider)
        suggestions = screen_methodologies(_INEGOL_DESCRIPTION, project_input=pi)
        assert len(suggestions) > 0
        assert suggestions[0].methodology_id == "ACM0022"
        assert suggestions[0].confidence > 0.5


class TestDocToDraftE2E:
    def test_extract_then_draft_completes(self):
        """Full pipeline: extract -> draft using DemoProvider."""
        extraction_provider = _mock_extraction_provider(_MOCK_EXTRACTION_YAML)
        pi = extract_project_input(_INEGOL_DESCRIPTION, extraction_provider)

        orch = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=pi,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        run = orch.run()
        assert len(run.sections) > 0
        assert run.provider == "demo"
        assert run.project_name == pi.project.project_name

    def test_extract_then_screen_then_draft(self):
        """Full pipeline: extract -> screen -> draft."""
        extraction_provider = _mock_extraction_provider(_MOCK_EXTRACTION_YAML)
        pi = extract_project_input(_INEGOL_DESCRIPTION, extraction_provider)

        suggestions = screen_methodologies(_INEGOL_DESCRIPTION, project_input=pi)
        assert suggestions[0].methodology_id == "ACM0022"

        pi.suggested_methodologies = suggestions

        orch = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=pi,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        run = orch.run()
        assert len(run.sections) > 0
        assert pi.suggested_methodologies is not None
        assert pi.suggested_methodologies[0].methodology_id == "ACM0022"

    def test_extract_draft_review_completes(self, tmp_path):
        """Full pipeline: extract -> draft -> review."""
        extraction_provider = _mock_extraction_provider(_MOCK_EXTRACTION_YAML)
        pi = extract_project_input(_INEGOL_DESCRIPTION, extraction_provider)

        orch = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=pi,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
            assumption_burden_path=tmp_path / "assumption-burden.md",
        )
        orch.run()
        review = orch.run_review()
        assert "run_id" in review
        assert "review" in review

    def test_draft_run_saves_and_loads(self, tmp_path):
        """Extracted -> drafted run should serialize to JSON."""
        import json

        extraction_provider = _mock_extraction_provider(_MOCK_EXTRACTION_YAML)
        pi = extract_project_input(_INEGOL_DESCRIPTION, extraction_provider)

        orch = SectionOrchestrator(
            provider=DemoProvider(),
            project_input=pi,
            schema_path=_SCHEMA_PATH,
            prompts_dir=_PROMPTS_DIR,
        )
        run = orch.run()
        path = run.save(output_dir=tmp_path)
        assert path.exists()

        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["project_name"] == pi.project.project_name
        assert len(data["sections"]) == len(run.sections)
