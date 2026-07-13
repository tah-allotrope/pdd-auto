from pdd_agent.drafting.fact_substitution import FactSubstitutionEngine
from pdd_agent.phase05.benchmark import create_demo_project_input
from schemas.project_input import ProjectInput
import yaml


def _project(tmp_path):
    path = create_demo_project_input(tmp_path / "project.yaml")
    return ProjectInput.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def test_substitutes_explicit_project_facts(tmp_path):
    project = _project(tmp_path)
    result = FactSubstitutionEngine(project).adapt(
        "Old Plant in Old City is operated by Old Co under ACM0001.",
        source_name="reference-pdd",
        source_facts={
            "project_name": "Old Plant",
            "city": "Old City",
            "proponent_name": "Old Co",
            "methodology_ids": "ACM0001",
        },
    )
    assert project.project.project_name in result.text
    assert project.location.city in result.text
    assert "[ADAPTED FROM CORPUS: reference-pdd]" in result.text


def test_flags_retained_regulatory_references(tmp_path):
    result = FactSubstitutionEngine(_project(tmp_path)).adapt(
        "The environmental permit was approved in 2020.",
        source_name="reference-pdd",
    )
    assert "[REVIEW: substitution ambiguity" in result.text
