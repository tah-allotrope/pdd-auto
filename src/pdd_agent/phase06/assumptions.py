"""Helpers for loading, routing, and reporting spreadsheet assumption metadata."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ASSUMPTION_REPORT = REPO_ROOT / "reports" / "assumption-burden.md"

_SECTION_FIELD_RULES: dict[tuple[str, str], list[str]] = {
    ("1", "1.1"): [
        "project.project_name",
        "location.country",
        "location.region",
        "location.city",
        "technology.methodology_ids",
        "technology.installed_capacity_mw",
        "technology.annual_waste_throughput",
        "technology.energy_generation_mwh_year",
        "quantification.net_emissions_tco2e_per_year",
    ],
    ("1", "1.2"): ["technology.methodology_ids"],
    ("1", "1.3"): ["methodology_applicability.", "technology.", "location.country"],
    ("1", "1.4"): ["technology."],
    ("1", "1.5"): ["project.proponent_name", "project.proponent_contact_email"],
    ("1", "1.6"): ["project.other_entities"],
    ("1", "1.7"): ["project.ownership", "compliance_and_ownership.credit_ownership_statement"],
    ("1", "1.8"): ["dates.start_date"],
    ("1", "1.9"): ["dates.crediting_period_start", "dates.crediting_period_years"],
    ("1", "1.10"): ["technology.", "quantification.", "dates.crediting_period_years"],
    ("1", "1.11"): [
        "project.",
        "location.",
        "technology.",
        "quantification.net_emissions_tco2e_per_year",
    ],
    ("1", "1.12"): ["location."],
    ("1", "1.13"): ["location.", "technology.", "quantification.", "compliance_and_ownership."],
    ("1", "1.14"): ["location.country", "project.project_name", "compliance_and_ownership."],
    ("1", "1.15"): ["compliance_and_ownership.", "technology.installed_capacity_mw"],
    ("1", "1.16"): [
        "compliance_and_ownership.",
        "technology.landfill_diversion_claim",
        "technology.fuel_substitution_claim",
    ],
    ("1", "1.17"): ["sustainable_development."],
    ("1", "1.18"): ["project.", "technology.", "location."],
    ("2", "2.1"): ["safeguards.no_net_harm_statement"],
    ("2", "2.2"): [
        "safeguards.stakeholder_consultation_completed",
        "safeguards.stakeholder_consultation_date",
    ],
    ("2", "2.3"): ["safeguards.environmental_impact_assessment", "safeguards.eia_reference"],
    ("2", "2.4"): ["safeguards.stakeholder_consultation_completed"],
    ("2", "2.5"): ["safeguards."],
    ("3", "3.1"): ["technology.methodology_ids"],
    ("3", "3.2"): ["methodology_applicability.", "technology.", "location.country"],
    ("3", "3.3"): [
        "location.",
        "dates.",
        "technology.methodology_ids",
        "technology.annual_waste_throughput",
    ],
    ("3", "3.4"): ["technology.", "quantification.", "location.", "compliance_and_ownership."],
    ("3", "3.5"): ["project.", "technology.", "quantification.", "compliance_and_ownership."],
    ("3", "3.6"): ["methodology_applicability.deviation_from_methodology"],
    ("4", "4.1"): ["quantification.", "technology.annual_waste_throughput", "location.landfill_"],
    ("4", "4.2"): [
        "quantification.project_emissions_tco2e_per_year",
        "technology.energy_generation_mwh_year",
    ],
    ("4", "4.3"): ["technology.", "quantification.leakage_tco2e_per_year", "location.landfill_"],
    ("4", "4.4"): ["quantification.", "dates.crediting_period_years"],
    ("5", "5.1"): ["monitoring.", "technology.", "quantification.grid_emission_factor"],
    ("5", "5.2"): ["monitoring.", "technology.", "quantification."],
    ("5", "5.3"): ["monitoring."],
}

_SECTION_DEFAULT_RULES: dict[str, list[str]] = {
    "1": [
        "project.",
        "location.",
        "dates.",
        "technology.",
        "compliance_and_ownership.",
        "sustainable_development.",
    ],
    "2": ["safeguards."],
    "3": [
        "methodology_applicability.",
        "technology.",
        "location.",
        "dates.",
        "quantification.",
        "compliance_and_ownership.",
    ],
    "4": ["quantification.", "technology.", "dates.", "location.landfill_"],
    "5": ["monitoring.", "technology.", "quantification."],
}


def resolve_assumptions_path(project_input_path: Path | str) -> Path | None:
    project_input_path = Path(project_input_path)
    suffixes = [".assumptions.yaml", ".assumptions.yml"]
    for suffix in suffixes:
        candidate = project_input_path.with_name(f"{project_input_path.stem}{suffix}")
        if candidate.exists():
            return candidate
    return None


def load_assumption_register(path: Path | str | None) -> dict[str, Any] | None:
    if path is None:
        return None
    resolved = Path(path)
    if not resolved.exists():
        return None
    with open(resolved, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def relevant_fact_entries(
    assumption_register: dict[str, Any] | None,
    section_id: str,
    sub_section_id: str | None,
) -> list[dict[str, Any]]:
    if not assumption_register:
        return []

    rules = _SECTION_FIELD_RULES.get((section_id, sub_section_id or ""))
    if not rules:
        rules = _SECTION_DEFAULT_RULES.get(section_id, [])

    blocked_paths = set(assumption_register.get("guardrails", {}).get("blocked_review_paths", []))
    matches: list[dict[str, Any]] = []
    for entry in assumption_register.get("assumptions", []):
        field_path = entry.get("field_path", "")
        if any(_matches_rule(field_path, rule) for rule in rules):
            enriched = dict(entry)
            enriched["blocked_review"] = field_path in blocked_paths
            matches.append(enriched)
    return matches


def summarize_fact_sources(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(entry.get("source_type", "unknown") for entry in entries)
    return dict(sorted(counts.items()))


def synthetic_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        entry
        for entry in entries
        if entry.get("source_type") in {"synthetic_assumption", "demo_default"}
    ]


def output_ref_for_section(content_class: str) -> str:
    if content_class == "QUANTITATIVE":
        return "section table"
    if content_class == "FACTUAL":
        return "section facts"
    return "section narrative"


def summarize_section_burden(section_payload: dict[str, Any]) -> dict[str, Any]:
    synthetic = section_payload.get("synthetic_uses", [])
    blocked_count = sum(1 for item in synthetic if item.get("blocked_review"))
    material = blocked_count > 0 or section_payload.get("review_sensitivity") in {
        "HIGH",
        "CRITICAL",
    }
    return {
        "section_key": _section_key(
            section_payload.get("section_id", ""), section_payload.get("sub_section_id", "")
        ),
        "synthetic_count": len(synthetic),
        "blocked_count": blocked_count,
        "material": material and len(synthetic) > 0,
        "source_counts": summarize_fact_sources(section_payload.get("fact_provenance", [])),
    }


def render_assumption_burden_report(run_data: dict[str, Any]) -> str:
    sections = run_data.get("sections", [])
    rows = [summarize_section_burden(section) for section in sections]
    rows_with_synthetic = [row for row in rows if row["synthetic_count"] > 0]
    material = [row for row in rows_with_synthetic if row["material"]]
    boilerplate = [row for row in rows_with_synthetic if not row["material"]]

    lines = [
        "# Assumption Burden Report",
        "",
        f"- Run ID: `{run_data.get('run_id', 'unknown')}`",
        f"- Project: `{run_data.get('project_name', 'unknown')}`",
        f"- Sections with synthetic or demo inputs: `{len(rows_with_synthetic)}`",
        f"- Material review gaps: `{len(material)}`",
        f"- Lower-risk boilerplate fills: `{len(boilerplate)}`",
        "",
        "## Material Domain Gaps",
        "",
    ]

    if material:
        for row in material:
            counts = ", ".join(f"{key}={value}" for key, value in row["source_counts"].items())
            lines.append(
                f"- `{row['section_key']}` synthetic=`{row['synthetic_count']}` blocked=`{row['blocked_count']}` sources=`{counts}`"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Lower-Risk Boilerplate Fills", ""])
    if boilerplate:
        for row in boilerplate:
            counts = ", ".join(f"{key}={value}" for key, value in row["source_counts"].items())
            lines.append(
                f"- `{row['section_key']}` synthetic=`{row['synthetic_count']}` blocked=`{row['blocked_count']}` sources=`{counts}`"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Section Detail", ""])
    if rows_with_synthetic:
        for row in rows_with_synthetic:
            counts = ", ".join(f"{key}={value}" for key, value in row["source_counts"].items())
            lines.append(
                f"- `{row['section_key']}` material=`{row['material']}` synthetic=`{row['synthetic_count']}` blocked=`{row['blocked_count']}` sources=`{counts}`"
            )
    else:
        lines.append("- No synthetic or demo-derived section inputs were recorded.")

    return "\n".join(lines) + "\n"


def write_assumption_burden_report(
    run_data: dict[str, Any], output_path: Path | str | None = None
) -> Path:
    output_path = Path(output_path or DEFAULT_ASSUMPTION_REPORT)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_assumption_burden_report(run_data), encoding="utf-8")
    return output_path


def _matches_rule(field_path: str, rule: str) -> bool:
    if rule.endswith(".") or rule.endswith("_"):
        return field_path.startswith(rule)
    return field_path == rule


def _section_key(section_id: str, sub_section_id: str) -> str:
    return sub_section_id or section_id
