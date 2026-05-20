"""Tests validating the Inegol demo ProjectInput YAML loads and validates correctly."""

import pytest
from pathlib import Path
import yaml
from pydantic import ValidationError

from schemas.project_input import ProjectInput


@pytest.fixture
def inegol_input():
    yaml_path = Path("configs/demo/inegol_project_input.yaml")
    assert yaml_path.exists(), f"Inegol input YAML not found at {yaml_path}"
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return ProjectInput(**data)


class TestInegolIdentity:
    def test_project_name(self, inegol_input):
        assert inegol_input.project.project_name == "INEGOL INTEGRATED SOLID WASTE STORAGE AND DISPOSAL FACILITY"

    def test_project_id_vcs(self, inegol_input):
        assert inegol_input.project.project_id_vcs == "3908"

    def test_proponent(self, inegol_input):
        assert inegol_input.project.proponent_name == "BIOTREND Çevre ve Enerji Yatırımları Anonim Şirketi"
        assert inegol_input.project.proponent_contact_email == "akif.demir@biotrendenerji.com.tr"

    def test_other_entities(self, inegol_input):
        assert len(inegol_input.project.other_entities) == 3
        assert "MUNDO VERDE CLIMATE SA" in inegol_input.project.other_entities

    def test_ownership(self, inegol_input):
        assert "MUNDO VERDE CLIMATE SA" in inegol_input.project.ownership
        assert "Doğu Star Elektrik Üretim A.Ş." in inegol_input.project.ownership

    def test_vcs_version(self, inegol_input):
        assert inegol_input.project.vcs_standard_version == "v4.7"

    def test_prepared_by(self, inegol_input):
        assert inegol_input.project.prepared_by == "Gaia Climate Finansal Danışmanlık Hizmetleri ve Ticaret A.Ş."

    def test_audit_history(self, inegol_input):
        assert len(inegol_input.project.audit_history) == 1
        entry = inegol_input.project.audit_history[0]
        assert entry.audit_type == "validation"
        assert entry.vvb_name == "Earthood"
        assert entry.number_of_years == 7


class TestInegolLocation:
    def test_country_region_city(self, inegol_input):
        assert inegol_input.location.country == "Türkiye"
        assert inegol_input.location.region == "Bursa Province"
        assert inegol_input.location.city == "İnegöl District"

    def test_coordinates(self, inegol_input):
        assert inegol_input.location.latitude == pytest.approx(40.1505)
        assert inegol_input.location.longitude == pytest.approx(29.5810)

    def test_site_area(self, inegol_input):
        assert inegol_input.location.site_area_m2 == pytest.approx(38490.14)

    def test_grid_connection(self, inegol_input):
        assert inegol_input.location.grid_connection_point == "İnegöl TM No-154/34.5 kV substation"

    def test_boundary_coordinates_count(self, inegol_input):
        assert len(inegol_input.location.boundary_coordinates) == 10


class TestInegolDates:
    def test_start_and_crediting(self, inegol_input):
        assert inegol_input.dates.start_date == "2020-12-31"
        assert inegol_input.dates.crediting_period_start == "2020-12-31"
        assert inegol_input.dates.crediting_period_years == 7
        assert inegol_input.dates.project_scale_small is False


class TestInegolTechnology:
    def test_methodology(self, inegol_input):
        assert inegol_input.technology.methodology_ids == ["ACM0022"]

    def test_technology_type(self, inegol_input):
        assert inegol_input.technology.technology_type == "combined_wte_ad"

    def test_waste_type(self, inegol_input):
        assert inegol_input.technology.waste_type == ["municipal_solid_waste"]

    def test_capacity_and_throughput(self, inegol_input):
        assert inegol_input.technology.installed_capacity_mw == pytest.approx(8.484)
        assert inegol_input.technology.annual_waste_throughput == pytest.approx(262970.37)
        assert inegol_input.technology.energy_generation_mwh_year == pytest.approx(49935.315)

    def test_landfill_diversion(self, inegol_input):
        assert inegol_input.technology.landfill_diversion_claim is True
        assert inegol_input.technology.fuel_substitution_claim is False

    def test_gas_engines(self, inegol_input):
        assert len(inegol_input.technology.gas_engine_commissioning) == 6
        assert inegol_input.technology.gas_engine_commissioning[0].model == "CAT 3412C (Engine 1)"

    def test_rdf_capacity(self, inegol_input):
        assert inegol_input.technology.rdf_capacity is not None
        assert inegol_input.technology.rdf_capacity.max_capacity_tph == pytest.approx(27)
        assert inegol_input.technology.rdf_capacity.planned_2024_tpd == pytest.approx(93)
        assert inegol_input.technology.rdf_capacity.planned_2035_tpd == pytest.approx(125)

    def test_biomethanization_fraction(self, inegol_input):
        assert inegol_input.technology.biomethanization_suitable_fraction == pytest.approx(0.45)


class TestInegolApplicability:
    def test_eligibility_checklist(self, inegol_input):
        checklist = inegol_input.methodology_applicability.eligibility_checklist
        assert isinstance(checklist, dict)
        assert all(checklist.values())
        assert len(checklist) >= 11

    def test_no_deviation(self, inegol_input):
        assert inegol_input.methodology_applicability.deviation_from_methodology is None


class TestInegolQuantification:
    def test_tbd_fields(self, inegol_input):
        assert inegol_input.quantification.baseline_emissions_tco2e_per_year is None
        assert inegol_input.quantification.project_emissions_tco2e_per_year is None
        assert inegol_input.quantification.net_emissions_tco2e_per_year is None
        assert inegol_input.quantification.grid_emission_factor is None

    def test_grid_emission_factor_source(self, inegol_input):
        assert inegol_input.quantification.grid_emission_factor_source is None


class TestInegolMonitoring:
    def test_parameters_count(self, inegol_input):
        assert len(inegol_input.monitoring.parameters_monitored) == 10

    def test_first_parameter(self, inegol_input):
        p = inegol_input.monitoring.parameters_monitored[0]
        assert p["name"] == "W_MSW,y"
        assert p["unit"] == "tonnes"

    def test_equipment_list(self, inegol_input):
        assert "Weighbridge" in inegol_input.monitoring.monitoring_equipment
        assert "SCADA" in inegol_input.monitoring.monitoring_equipment

    def test_data_management(self, inegol_input):
        assert "VCS" in inegol_input.monitoring.data_management


class TestInegolSafeguards:
    def test_consultation_not_completed(self, inegol_input):
        assert inegol_input.safeguards.stakeholder_consultation_completed is False
        assert inegol_input.safeguards.stakeholder_consultation_date is None

    def test_eia_not_done(self, inegol_input):
        assert inegol_input.safeguards.environmental_impact_assessment is False
        assert inegol_input.safeguards.eia_reference is None


class TestInegolCompliance:
    def test_ownership(self, inegol_input):
        assert "MUNDO VERDE CLIMATE SA" in inegol_input.compliance_and_ownership.credit_ownership_statement
        assert inegol_input.compliance_and_ownership.no_participation_other_programs is True
        assert inegol_input.compliance_and_ownership.no_other_forms_of_credit is True
        assert inegol_input.compliance_and_ownership.double_counting_risk is False


class TestInegolSD:
    def test_sd_contributions(self, inegol_input):
        assert len(inegol_input.sustainable_development.sd_contributions) == 4
        assert "Climate mitigation" in inegol_input.sustainable_development.sd_contributions


class TestInegolSummary:
    def test_summary_includes_key_info(self, inegol_input):
        summary = inegol_input.summary()
        assert "INEGOL" in summary
        assert "Türkiye" in summary
        assert "ACM0022" in summary
        assert "8.484" in summary
