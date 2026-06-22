"""Tests for LLM-based document extraction pipeline."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from pdd_agent.ingest.extract import (
    extract_project_input,
    _read_text_from_file,
    _parse_yaml_from_response,
    _clean_missing_markers,
    _apply_schema_defaults,
    _build_extraction_prompt,
    ExtractionError,
)
from schemas.project_input import ProjectInput, ExtractionProvenance, SuggestedMethodology


_SAMPLE_YAML_RESPONSE = """\
project:
  project_name: "Inegol WTE Project"
  proponent_name: "BIOTREND"
  proponent_contact_email: "info@biotrend.com"
  ownership: "BIOTREND owns 100%"
location:
  country: "Turkey"
  region: "Bursa"
  city: "Inegol"
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
  data_management: "Digital records system"
safeguards:
  no_net_harm_statement: "No net harm confirmed"
compliance_and_ownership:
  credit_ownership_statement: "BIOTREND owns all credits"
sustainable_development:
  sd_contributions: ["SDG-7", "SDG-13"]
_extraction:
  extracted_fields: ["project.project_name", "location.country", "technology.methodology_ids"]
  defaulted_fields: ["quantification"]
  missing_fields: []
  confidence_notes: "High quality extraction"
"""

_SAMPLE_YAML_WITH_MISSING = """\
project:
  project_name: "Test Project"
  proponent_name: "Test Corp"
  proponent_contact_email: "[MISSING]"
  ownership: "Test Corp"
location:
  country: "Vietnam"
  region: "[MISSING]"
  city: "Hanoi"
  latitude: 21.0
  longitude: 105.8
dates:
  start_date: "2024-01-01"
  crediting_period_start: "2024-06-01"
  crediting_period_years: 10
technology:
  methodology_ids: ["ACM0022"]
  technology_type: "anaerobic_digestion"
  waste_type: ["municipal_solid_waste"]
  annual_waste_throughput: 50000
  installed_capacity_mw: 3.0
methodology_applicability:
  eligibility_checklist: {}
quantification: {}
monitoring:
  parameters_monitored: []
  data_management: "[MISSING]"
safeguards:
  no_net_harm_statement: "[MISSING]"
compliance_and_ownership:
  credit_ownership_statement: "[MISSING]"
sustainable_development: {}
_extraction:
  extracted_fields: ["project.project_name"]
  defaulted_fields: []
  missing_fields: ["proponent_contact_email", "location.region", "monitoring.data_management"]
"""


class TestReadTextFromFile:
    def test_read_txt_file(self, tmp_path):
        txt = tmp_path / "test.txt"
        txt.write_text("Hello world project description", encoding="utf-8")
        result = _read_text_from_file(txt)
        assert "Hello world" in result

    def test_read_nonexistent_raises(self):
        with pytest.raises(Exception):
            _read_text_from_file(Path("/nonexistent/file.txt"))

    @patch("pdd_agent.ingest.extract._extract_docx_text", return_value="DOCX content")
    def test_read_docx_dispatches(self, mock_docx, tmp_path):
        docx = tmp_path / "test.docx"
        docx.write_bytes(b"PK\x03\x04")
        result = _read_text_from_file(docx)
        assert result == "DOCX content"
        mock_docx.assert_called_once()

    @patch("pdd_agent.ingest.extract._extract_pdf_text", return_value="PDF content")
    def test_read_pdf_dispatches(self, mock_pdf, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        result = _read_text_from_file(pdf)
        assert result == "PDF content"
        mock_pdf.assert_called_once()


class TestParseYamlFromResponse:
    def test_parse_valid_yaml(self):
        result = _parse_yaml_from_response(_SAMPLE_YAML_RESPONSE)
        assert result["project"]["project_name"] == "Inegol WTE Project"

    def test_parse_fenced_yaml(self):
        fenced = f"```yaml\n{_SAMPLE_YAML_RESPONSE}\n```"
        result = _parse_yaml_from_response(fenced)
        assert result["project"]["project_name"] == "Inegol WTE Project"

    def test_parse_error_response(self):
        error_yaml = '_error: "Not a PDD"\n_reason: "Document is a recipe"'
        with pytest.raises(ExtractionError, match="LLM reported extraction error"):
            _parse_yaml_from_response(error_yaml)

    def test_parse_invalid_yaml(self):
        with pytest.raises(ExtractionError, match="Failed to parse YAML"):
            _parse_yaml_from_response("{{invalid: yaml: [}")

    def test_parse_non_dict(self):
        with pytest.raises(ExtractionError, match="Expected YAML dict"):
            _parse_yaml_from_response("- item1\n- item2")


class TestCleanMissingMarkers:
    def test_replaces_missing_with_none(self):
        data = {"field": "[MISSING]", "nested": {"sub": "[MISSING]"}}
        cleaned, missing = _clean_missing_markers(data)
        assert cleaned["field"] is None
        assert cleaned["nested"]["sub"] is None
        assert "field" in missing
        assert "nested.sub" in missing

    def test_preserves_normal_values(self):
        data = {"field": "normal", "num": 42}
        cleaned, missing = _clean_missing_markers(data)
        assert cleaned["field"] == "normal"
        assert cleaned["num"] == 42
        assert missing == []

    def test_preserves_inference_markers(self):
        data = {"field": "[INFERENCE: assumed from context]"}
        cleaned, missing = _clean_missing_markers(data)
        assert "[INFERENCE:" in cleaned["field"]
        assert missing == []

    def test_handles_lists(self):
        data = {"items": ["good", "[MISSING]", "also good"]}
        cleaned, missing = _clean_missing_markers(data)
        assert cleaned["items"] == ["good", None, "also good"]
        assert len(missing) == 1


class TestApplySchemaDefaults:
    def test_fills_missing_sections(self):
        data = {"project": {"project_name": "Test"}}
        result = _apply_schema_defaults(data)
        assert "methodology_applicability" in result
        assert "quantification" in result
        assert "monitoring" in result
        assert "safeguards" in result

    def test_fills_technology_defaults(self):
        data = {"technology": {"methodology_ids": []}}
        result = _apply_schema_defaults(data)
        assert result["technology"]["waste_type"] == ["municipal_solid_waste"]
        assert result["technology"]["methodology_ids"] == ["UNKNOWN"]

    def test_preserves_existing_values(self):
        data = {
            "technology": {
                "methodology_ids": ["ACM0022"],
                "waste_type": ["kitchen_waste"],
                "annual_waste_throughput": 50000,
                "installed_capacity_mw": 5.0,
                "technology_type": "anaerobic_digestion",
            }
        }
        result = _apply_schema_defaults(data)
        assert result["technology"]["methodology_ids"] == ["ACM0022"]
        assert result["technology"]["waste_type"] == ["kitchen_waste"]


class TestBuildExtractionPrompt:
    def test_includes_document_text(self):
        prompt = _build_extraction_prompt("Test document content here")
        assert "Test document content here" in prompt
        assert "ProjectInput" in prompt

    def test_truncates_long_documents(self):
        long_text = "x" * 100_000
        prompt = _build_extraction_prompt(long_text)
        assert "truncated" in prompt


class TestExtractProjectInput:
    def _mock_provider(self, yaml_response: str):
        from pdd_agent.llm.provider import DraftSection
        provider = MagicMock()
        provider.draft_section.return_value = DraftSection(
            section_id="extract",
            sub_section_id="project_input",
            text=yaml_response,
            confidence="HIGH",
            provenance=["[EXTRACTION: document intake]"],
            issues=[],
            provider="mock",
        )
        return provider

    def test_extract_from_text_string(self):
        provider = self._mock_provider(_SAMPLE_YAML_RESPONSE)
        result = extract_project_input("Sample project description text", provider)
        assert isinstance(result, ProjectInput)
        assert result.project.project_name == "Inegol WTE Project"
        assert result.extraction_provenance is not None

    def test_extract_from_text_file(self, tmp_path):
        txt = tmp_path / "project.txt"
        txt.write_text("A waste to energy project in Turkey", encoding="utf-8")
        provider = self._mock_provider(_SAMPLE_YAML_RESPONSE)
        result = extract_project_input(txt, provider)
        assert result.project.project_name == "Inegol WTE Project"
        assert result.extraction_provenance.source_document == str(txt)

    def test_extract_with_missing_fields(self):
        provider = self._mock_provider(_SAMPLE_YAML_WITH_MISSING)
        result = extract_project_input("Project description", provider)
        assert isinstance(result, ProjectInput)
        assert result.extraction_provenance is not None
        assert len(result.extraction_provenance.missing_fields) > 0

    def test_extract_empty_text_raises(self):
        provider = MagicMock()
        with pytest.raises(ExtractionError, match="empty"):
            extract_project_input("   ", provider)

    def test_extract_nonexistent_file_raises(self):
        provider = MagicMock()
        with pytest.raises(ExtractionError, match="not found"):
            extract_project_input(Path("/nonexistent/doc.txt"), provider)

    def test_extract_provider_error(self):
        from pdd_agent.llm.provider import DraftSection
        provider = MagicMock()
        provider.draft_section.return_value = DraftSection(
            section_id="extract",
            sub_section_id="project_input",
            text="[OPENAI ERROR — extract] Provider error: auth failed",
            confidence="UNSUPPORTED",
            provenance=[],
            issues=["ERROR"],
            provider="mock",
        )
        with pytest.raises(ExtractionError, match="Provider returned error"):
            extract_project_input("Some project", provider)

    def test_extraction_provenance_populated(self):
        provider = self._mock_provider(_SAMPLE_YAML_RESPONSE)
        result = extract_project_input("Test", provider)
        prov = result.extraction_provenance
        assert prov is not None
        assert "project.project_name" in prov.extracted_fields
        assert "quantification" in prov.defaulted_fields


class TestSuggestedMethodologyModel:
    def test_create_suggested_methodology(self):
        sm = SuggestedMethodology(
            methodology_id="ACM0022",
            name="Alternative Waste Treatment Processes",
            confidence=0.85,
            rationale="technology match; waste type match",
            active_status_source="verra_registry",
            version="v3.0",
        )
        assert sm.methodology_id == "ACM0022"
        assert sm.confidence == 0.85

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            SuggestedMethodology(
                methodology_id="X",
                name="X",
                confidence=1.5,
                rationale="X",
            )
        with pytest.raises(Exception):
            SuggestedMethodology(
                methodology_id="X",
                name="X",
                confidence=-0.1,
                rationale="X",
            )


class TestExtractionProvenanceModel:
    def test_create_provenance(self):
        prov = ExtractionProvenance(
            extracted_fields=["project.project_name"],
            defaulted_fields=["quantification"],
            missing_fields=["proponent_contact_email"],
            source_document="test.docx",
            extraction_model="gpt-4o",
        )
        assert len(prov.extracted_fields) == 1
        assert prov.source_document == "test.docx"

    def test_project_input_with_provenance(self):
        from tests.test_prompt_assembly import _minimal_project_dict
        data = _minimal_project_dict()
        pi = ProjectInput(**data)
        assert pi.extraction_provenance is None
        assert pi.suggested_methodologies is None
