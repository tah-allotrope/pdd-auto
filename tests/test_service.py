"""API contract tests for the PDD Agent FastAPI service.

All tests use the ``demo`` provider so no external API keys are required.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from fastapi.testclient import TestClient

from pdd_agent.service import main as service_main
from pdd_agent.service.main import app
from schemas.project_input import ProjectInput


CLIENT = TestClient(app)


@pytest.fixture
def minimal_project_yaml(tmp_path: Path) -> Path:
    project = {
        "project": {
            "project_name": "Service Test WTE",
            "proponent_name": "Test Proponent",
            "proponent_contact_email": "test@example.com",
            "ownership": "Test Proponent owns 100%",
        },
        "location": {
            "country": "Turkey",
            "region": "Bursa",
            "city": "Inegol",
            "latitude": 40.08,
            "longitude": 29.51,
        },
        "dates": {
            "start_date": "2020-12-31",
            "crediting_period_start": "2021-06-01",
            "crediting_period_years": 7,
        },
        "technology": {
            "methodology_ids": ["ACM0022"],
            "technology_type": "incineration_with_energy_recovery",
            "waste_type": ["municipal_solid_waste"],
            "annual_waste_throughput": 100000.0,
            "installed_capacity_mw": 8.0,
        },
        "methodology_applicability": {
            "eligibility_checklist": {"applicable": True},
        },
        "quantification": {
            "baseline_emissions_tco2e_per_year": 150000.0,
            "project_emissions_tco2e_per_year": 50000.0,
            "leakage_tco2e_per_year": 0.0,
            "net_emissions_tco2e_per_year": 100000.0,
            "crediting_period_total_tco2e": 700000.0,
        },
        "monitoring": {
            "parameters_monitored": [
                {
                    "name": "Waste throughput",
                    "unit": "tonnes",
                    "frequency": "daily",
                    "method": "weighbridge",
                    "data_source": "plant records",
                }
            ],
            "data_management": "Digital records",
        },
        "safeguards": {
            "no_net_harm_statement": "No net harm analysis completed.",
        },
        "compliance_and_ownership": {
            "credit_ownership_statement": "Test Proponent owns credits",
        },
        "sustainable_development": {
            "sd_contributions": ["SDG-7", "SDG-13"],
        },
    }
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(project), encoding="utf-8")
    return path


@pytest.fixture
def service_runs_dir(tmp_path: Path, monkeypatch):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(service_main, "RUNS_DIR", runs_dir)
    monkeypatch.setenv("PDD_SERVICE_RUNS_DIR", str(runs_dir))
    return runs_dir


@pytest.fixture
def uploaded_project_input(minimal_project_yaml, tmp_path: Path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(service_main, "REPO_ROOT", tmp_path)
    return minimal_project_yaml


class TestWebUIRoutes:
    def test_root_redirects_to_dashboard(self):
        response = CLIENT.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/dashboard"

    def test_dashboard_renders(self):
        response = CLIENT.get("/dashboard")
        assert response.status_code == 200
        assert "PDD Draft Runs" in response.text


class TestIntakeRoutes:
    def test_intake_document_extracts_project_input(self, tmp_path: Path):
        doc = tmp_path / "project.txt"
        doc.write_text(
            "Inegol waste-to-energy project in Bursa, Turkey. "
            "Treats 100,000 tonnes of municipal solid waste per year.",
            encoding="utf-8",
        )

        with patch(
            "pdd_agent.service.main.extract_project_input"
        ) as mock_extract:
            project_input = ProjectInput.model_validate(
                {
                    "project": {
                        "project_name": "Mock Extracted Project",
                        "proponent_name": "Mock Proponent",
                        "proponent_contact_email": "mock@example.com",
                        "ownership": "Mock ownership",
                    },
                    "location": {
                        "country": "Turkey",
                        "region": "Bursa",
                        "city": "Inegol",
                        "latitude": 40.08,
                        "longitude": 29.51,
                    },
                    "dates": {
                        "start_date": "2020-12-31",
                        "crediting_period_start": "2021-06-01",
                        "crediting_period_years": 7,
                    },
                    "technology": {
                        "methodology_ids": ["ACM0022"],
                        "technology_type": "incineration_with_energy_recovery",
                        "waste_type": ["municipal_solid_waste"],
                        "annual_waste_throughput": 100000.0,
                        "installed_capacity_mw": 8.0,
                    },
                    "methodology_applicability": {"eligibility_checklist": {}},
                    "quantification": {
                        "baseline_emissions_tco2e_per_year": 150000.0,
                        "project_emissions_tco2e_per_year": 50000.0,
                        "leakage_tco2e_per_year": 0.0,
                        "net_emissions_tco2e_per_year": 100000.0,
                        "crediting_period_total_tco2e": 700000.0,
                    },
                    "monitoring": {
                        "parameters_monitored": [
                            {
                                "name": "Waste throughput",
                                "unit": "tonnes",
                                "frequency": "daily",
                                "method": "weighbridge",
                                "data_source": "plant records",
                            }
                        ],
                        "data_management": "Digital records",
                    },
                    "safeguards": {"no_net_harm_statement": "No net harm."},
                    "compliance_and_ownership": {
                        "credit_ownership_statement": "Mock owns credits"
                    },
                    "sustainable_development": {},
                }
            )
            mock_extract.return_value = project_input

            with open(doc, "rb") as f:
                response = CLIENT.post("/api/intake/document", files={"file": f})

        assert response.status_code == 200
        data = response.json()
        assert "project_input" in data
        assert data["provider"] == "demo"
        assert "yaml" in data

    def test_intake_spreadsheet_without_upload_uses_default_cache(self, tmp_path: Path, monkeypatch):
        from pdd_agent import phase06

        cache_dir = tmp_path / "spreadsheets"
        cache_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(
            phase06.spreadsheet_mapper,
            "DEFAULT_SPREADSHEET_CACHE_DIR",
            str(cache_dir),
        )
        monkeypatch.setattr(service_main, "REPO_ROOT", tmp_path)

        workbook = cache_dir / "sample.xlsx"
        _make_minimal_workbook(workbook)

        response = CLIENT.post("/api/intake/spreadsheet", data={"candidate_key": "soc-son"})
        assert response.status_code == 200
        data = response.json()
        assert "project_yaml_path" in data
        assert Path(data["project_yaml_path"]).exists()


class TestRunLifecycle:
    def test_create_run_returns_run_id(self, minimal_project_yaml, service_runs_dir, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(service_main, "REPO_ROOT", tmp_path)
        upload_dir = tmp_path / "data" / "source_inputs" / "service_uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        with open(minimal_project_yaml, "rb") as f:
            response = CLIENT.post(
                "/api/runs",
                files={"project_input_yaml": ("project.yaml", f, "application/x-yaml")},
                data={"provider_name": "demo"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["provider"] == "demo"
        assert "run_id" in data

    def test_list_and_get_run_after_completion(
        self, minimal_project_yaml, service_runs_dir, tmp_path: Path, monkeypatch
    ):
        monkeypatch.setattr(service_main, "REPO_ROOT", tmp_path)
        upload_dir = tmp_path / "data" / "source_inputs" / "service_uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        with open(minimal_project_yaml, "rb") as f:
            create_response = CLIENT.post(
                "/api/runs",
                files={"project_input_yaml": ("project.yaml", f, "application/x-yaml")},
                data={"provider_name": "demo"},
            )

        run_id = create_response.json()["run_id"]

        # Wait for background task to finish.
        for _ in range(50):
            if _run_json_exists(service_runs_dir, run_id):
                break
            time.sleep(0.1)
        else:
            pytest.fail("Run JSON was not created")

        list_response = CLIENT.get("/api/runs")
        assert list_response.status_code == 200
        runs = list_response.json()["runs"]
        assert any(r["run_id"] == run_id for r in runs)

        detail_response = CLIENT.get(f"/api/runs/{run_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["run_id"] == run_id
        assert detail["project_name"] == "Service Test WTE"
        assert len(detail["sections"]) > 0


class TestSectionReview:
    @pytest.fixture
    def completed_run(self, minimal_project_yaml, service_runs_dir, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(service_main, "REPO_ROOT", tmp_path)
        upload_dir = tmp_path / "data" / "source_inputs" / "service_uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        with open(minimal_project_yaml, "rb") as f:
            create_response = CLIENT.post(
                "/api/runs",
                files={"project_input_yaml": ("project.yaml", f, "application/x-yaml")},
                data={"provider_name": "demo"},
            )

        run_id = create_response.json()["run_id"]
        for _ in range(50):
            if _run_json_exists(service_runs_dir, run_id):
                break
            time.sleep(0.1)
        else:
            pytest.fail("Run JSON was not created")

        return run_id

    def test_get_section_detail(self, completed_run):
        run_id = completed_run
        detail = CLIENT.get(f"/api/runs/{run_id}").json()
        section_key = detail["sections"][0]["key"]

        response = CLIENT.get(f"/api/runs/{run_id}/sections/{section_key}")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["section_key"] == section_key
        assert "text" in data

    def test_approve_section(self, completed_run):
        run_id = completed_run
        detail = CLIENT.get(f"/api/runs/{run_id}").json()
        section_key = detail["sections"][0]["key"]

        response = CLIENT.post(f"/api/runs/{run_id}/sections/{section_key}/approve")
        assert response.status_code == 200
        assert response.json()["state"] == "approved"

        section = CLIENT.get(f"/api/runs/{run_id}/sections/{section_key}").json()
        assert section["state"] == "approved"

    def test_edit_section_persists_text_and_provenance(self, completed_run):
        run_id = completed_run
        detail = CLIENT.get(f"/api/runs/{run_id}").json()
        section_key = detail["sections"][0]["key"]

        new_text = "This text was edited via the service API."
        response = CLIENT.post(
            f"/api/runs/{run_id}/sections/{section_key}/edit",
            data={"text": new_text},
        )
        assert response.status_code == 200
        assert response.json()["edited"] is True

        section = CLIENT.get(f"/api/runs/{run_id}/sections/{section_key}").json()
        assert section["text"] == new_text
        assert any("HUMAN EDIT" in p for p in section["provenance"])

    def test_edit_and_approve_section(self, completed_run):
        run_id = completed_run
        detail = CLIENT.get(f"/api/runs/{run_id}").json()
        section_key = detail["sections"][0]["key"]

        response = CLIENT.post(
            f"/api/runs/{run_id}/sections/{section_key}/edit",
            data={"text": "Edited and approved text.", "approve": "true"},
        )
        assert response.status_code == 200
        assert response.json()["approved"] is True

        section = CLIENT.get(f"/api/runs/{run_id}/sections/{section_key}").json()
        assert section["state"] == "approved"

    def test_redraft_section_returns_status(self, completed_run):
        run_id = completed_run
        detail = CLIENT.get(f"/api/runs/{run_id}").json()
        section_key = detail["sections"][0]["key"]

        response = CLIENT.post(f"/api/runs/{run_id}/sections/{section_key}/redraft")
        assert response.status_code == 200
        assert response.json()["status"] == "redrafting"


class TestDocxExport:
    def test_docx_export_force_override(
        self, minimal_project_yaml, service_runs_dir, tmp_path: Path, monkeypatch
    ):
        monkeypatch.setattr(service_main, "REPO_ROOT", tmp_path)
        # Deliberately do NOT monkeypatch docx_export._DRAFT_RUNS_DIR here: the
        # service must locate the run JSON via the real runs_dir it threads
        # into export_run_to_docx(), not via a redirected module constant.
        # This is a regression test for a bug found during the PHASE-06 rice
        # pilot manual round-trip: export_run_to_docx() ignored a passed
        # runs_dir entirely and always looked in the default data/runs,
        # raising FileNotFoundError for any service run persisted elsewhere.
        upload_dir = tmp_path / "data" / "source_inputs" / "service_uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        with open(minimal_project_yaml, "rb") as f:
            create_response = CLIENT.post(
                "/api/runs",
                files={"project_input_yaml": ("project.yaml", f, "application/x-yaml")},
                data={"provider_name": "demo"},
            )

        run_id = create_response.json()["run_id"]
        for _ in range(50):
            if _run_json_exists(service_runs_dir, run_id):
                break
            time.sleep(0.1)
        else:
            pytest.fail("Run JSON was not created")

        # Gated export should be blocked.
        gated = CLIENT.get(f"/api/runs/{run_id}/docx")
        assert gated.status_code == 403

        # Force export should succeed.
        response = CLIENT.get(f"/api/runs/{run_id}/docx?force=1")
        assert response.status_code == 200
        assert response.headers["content-type"] == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )


class TestProviderSelection:
    def test_anthropic_without_key_falls_back_to_demo(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("PDD_MAX_COST_USD", raising=False)

        provider = service_main._get_provider("anthropic")

        assert provider.name == "demo"
        assert service_main.provider_status()["reason"] == "missing_api_key"

    def test_anthropic_with_key_but_no_cost_ceiling_falls_back_to_demo(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.delenv("PDD_MAX_COST_USD", raising=False)

        provider = service_main._get_provider("anthropic")

        assert provider.name == "demo"
        assert service_main.provider_status()["reason"] == "missing_cost_ceiling"

    def test_ollama_needs_no_key_or_ceiling(self, monkeypatch):
        monkeypatch.delenv("PDD_MAX_COST_USD", raising=False)

        provider = service_main._get_provider("ollama")

        assert provider.name == "ollama"
        assert service_main.provider_status()["reason"] is None

    def test_unset_provider_defaults_to_demo_with_no_reason(self, monkeypatch):
        monkeypatch.delenv("PDD_SERVICE_PROVIDER", raising=False)

        provider = service_main._get_provider()

        assert provider.name == "demo"
        assert service_main.provider_status()["reason"] is None

    def test_unknown_provider_name_falls_back_to_demo(self):
        provider = service_main._get_provider("totally-unknown")

        assert provider.name == "demo"
        assert service_main.provider_status()["reason"] == "unknown_provider"


class TestPersistenceDependencyInjection:
    def test_importing_service_does_not_monkeypatch_draft_run_save(self):
        from pdd_agent.llm.provider import DraftRun
        import inspect

        # DraftRun.save must be the class's own method, not a module-level
        # rebinding performed at service import time.
        source_file = inspect.getsourcefile(DraftRun.save)
        assert source_file is not None
        assert "service" not in source_file.replace("\\", "/")

    def test_importing_service_does_not_monkeypatch_review_state_store(self):
        from pdd_agent.review.states import ReviewStateStore
        import inspect

        source_file = inspect.getsourcefile(ReviewStateStore.save)
        assert source_file is not None
        assert "service" not in source_file.replace("\\", "/")

    def test_run_creates_status_json_in_service_runs_dir(
        self, minimal_project_yaml, service_runs_dir, tmp_path: Path, monkeypatch
    ):
        monkeypatch.setattr(service_main, "REPO_ROOT", tmp_path)
        upload_dir = tmp_path / "data" / "source_inputs" / "service_uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        with open(minimal_project_yaml, "rb") as f:
            create_response = CLIENT.post(
                "/api/runs",
                files={"project_input_yaml": ("project.yaml", f, "application/x-yaml")},
                data={"provider_name": "demo"},
            )
        run_id = create_response.json()["run_id"]

        for _ in range(50):
            if _run_json_exists(service_runs_dir, run_id):
                break
            time.sleep(0.1)
        else:
            pytest.fail("Run JSON was not created")

        status_path = service_runs_dir / f"{run_id}.status.json"
        assert status_path.exists()
        payload = json.loads(status_path.read_text(encoding="utf-8"))
        assert payload["status"] == "complete"


class TestStatusLifecycle:
    def test_orphaned_running_status_is_swept_to_failed(self, service_runs_dir):
        run_id = "run-orphan-test"
        (service_runs_dir / f"{run_id}.json").write_text("{}", encoding="utf-8")
        status_path = service_runs_dir / f"{run_id}.status.json"
        status_path.write_text(json.dumps({"status": "running"}), encoding="utf-8")

        service_main.sweep_orphaned_runs()

        payload = json.loads(status_path.read_text(encoding="utf-8"))
        assert payload["status"] == "failed"
        assert "orphaned" in payload["error"].lower()

    def test_non_running_status_is_untouched_by_sweep(self, service_runs_dir):
        run_id = "run-complete-test"
        status_path = service_runs_dir / f"{run_id}.status.json"
        status_path.write_text(json.dumps({"status": "complete"}), encoding="utf-8")

        service_main.sweep_orphaned_runs()

        payload = json.loads(status_path.read_text(encoding="utf-8"))
        assert payload["status"] == "complete"


def _run_json_exists(runs_dir: Path, run_id: str) -> bool:
    return (runs_dir / f"{run_id}.json").exists()


def _make_minimal_workbook(path: Path) -> None:
    from openpyxl import Workbook

    workbook = Workbook()
    projects = workbook.active
    assert projects is not None
    projects.title = "Projects"
    projects.append(
        [
            None,
            "Treatment capacity (tpd)",
            "Generated electricity\nMWh",
            "Estimated Annual Emission Reductions",
            "Wood and wood products\n(%, wet)",
            "Pulp, paper and cardboard\n(%, wet)",
            "Food, food waste, beverage and tobacco\n(%, wet)",
            "Textiles\n(%, wet)",
            "Garden, yard and park waste\n(%, wet)",
            "Glass\n(%, wet)",
            "Metal\n(%, wet)",
            "Plastics\n(%, wet)",
            "Rubber\n(%, wet)",
            "Other, inert waste\n(%, wet)",
            "Crediting Period Term",
            "VCS Methodology",
            "Ref",
            "Province/Country",
        ]
    )
    projects.append(
        [
            "Soc Son waste to power plant project",
            4000.0,
            388050.0,
            544076.0,
            0.0,
            2.7,
            51.9,
            1.6,
            0.0,
            0.5,
            0.9,
            3.0,
            1.3,
            38.1,
            "1st, 24/07/2022 - 23/07/2029",
            "ACM0022",
            "https://registry.verra.org/app/projectDetail/VCS/2567",
            "Vietnam",
        ]
    )
    workbook.save(path)
