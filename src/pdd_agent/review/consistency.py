"""Cross-section consistency checking for numeric and evidence claims.

Validates that numbers cited in one section are consistent with numbers
cited in other sections, and that evidence references are internally coherent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from schemas.project_input import ProjectInput


@dataclass
class ConsistencyFlag:
    section_a: str
    section_b: str
    field_name: str
    value_a: float | None
    value_b: float | None
    expected: float | None
    tolerance: float
    severity: str  # CRITICAL | HIGH | MEDIUM
    message: str


@dataclass
class ConsistencyReport:
    run_id: str
    flags: list[ConsistencyFlag] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(f.severity != "CRITICAL" for f in self.flags)

    @property
    def critical_flags(self) -> list[ConsistencyFlag]:
        return [f for f in self.flags if f.severity == "CRITICAL"]

    @property
    def high_flags(self) -> list[ConsistencyFlag]:
        return [f for f in self.flags if f.severity == "HIGH"]


def _extract_first_number(text: str) -> float | None:
    if not text:
        return None
    matches = re.findall(r"\d[\d,]*", text)
    if not matches:
        return None
    try:
        return float(matches[0].replace(",", ""))
    except ValueError:
        return None


def _extract_tco2e(text: str) -> list[float]:
    if not text:
        return []
    numbers = re.findall(r"([\d,]+\.?\d*)\s*(?:tCO2e|tCO2e/year|tCO2e/yr)", text, re.IGNORECASE)
    return [float(n.replace(",", "")) for n in numbers if n]


def check_quantitative_consistency(
    draft_sections: list[Any],
    project_input: ProjectInput | None,
    run_id: str,
) -> ConsistencyReport:
    """Check all quantitative consistency rules between sections.

    Args:
        draft_sections: List of DraftSection objects from orchestrator run.
        project_input: ProjectInput for absolute cross-checks against known values.
        run_id: Identifier for the report.
    """
    report = ConsistencyReport(run_id=run_id)

    section_map: dict[str, str] = {}
    for s in draft_sections:
        key = f"{s.section_id}.{s.sub_section_id}" if s.sub_section_id else s.section_id
        section_map[key] = s.text

    _check_net_emissions_cross_ref(section_map, project_input, report)
    _check_waste_throughput_consistency(section_map, project_input, report)
    _check_capacity_consistency(section_map, project_input, report)
    _check_crediting_period_total(section_map, project_input, report)
    _check_baseline_project_emissions_relation(section_map, report)

    return report


def _check_net_emissions_cross_ref(
    sections: dict[str, str],
    project_input: ProjectInput | None,
    report: ConsistencyReport,
) -> None:
    sec_1_10 = sections.get("1.10", "")
    sec_4_4 = sections.get("4.4", "")

    val_1_10 = _extract_first_number(sec_1_10)
    val_4_4 = _extract_first_number(sec_4_4)

    expected = project_input.quantification.net_emissions_tco2e_per_year if project_input else None

    if expected is not None and val_1_10 is not None and abs(val_1_10 - expected) > 0.01:
        report.flags.append(
            ConsistencyFlag(
                section_a="1.10",
                section_b="ProjectInput",
                field_name="net_emissions_tco2e_per_year",
                value_a=val_1_10,
                value_b=expected,
                expected=expected,
                tolerance=0.01,
                severity="CRITICAL",
                message=(
                    f"Section 1.10 net tCO2e ({val_1_10:,.0f}) does not match "
                    f"ProjectInput ({expected:,.0f}). Section 1.10 must be updated "
                    f"to match the validated quantification."
                ),
            )
        )

    if expected is not None and val_4_4 is not None and abs(val_4_4 - expected) > 0.01:
        report.flags.append(
            ConsistencyFlag(
                section_a="4.4",
                section_b="ProjectInput",
                field_name="net_emissions_tco2e_per_year",
                value_a=val_4_4,
                value_b=expected,
                expected=expected,
                tolerance=0.01,
                severity="CRITICAL",
                message=(
                    f"Section 4.4 net tCO2e ({val_4_4:,.0f}) does not match "
                    f"ProjectInput ({expected:,.0f}). Section 4.4 must be updated "
                    f"to match the validated quantification."
                ),
            )
        )

    if val_1_10 is not None and val_4_4 is not None and abs(val_1_10 - val_4_4) > 0.01:
        report.flags.append(
            ConsistencyFlag(
                section_a="1.10",
                section_b="4.4",
                field_name="net_emissions_tco2e_per_year",
                value_a=val_1_10,
                value_b=val_4_4,
                expected=None,
                tolerance=0.01,
                severity="CRITICAL",
                message=(
                    f"Section 1.10 ({val_1_10:,.0f}) and Section 4.4 ({val_4_4:,.0f}) "
                    f"report different net tCO2e values. These MUST match."
                ),
            )
        )


def _check_waste_throughput_consistency(
    sections: dict[str, str],
    project_input: ProjectInput | None,
    report: ConsistencyReport,
) -> None:
    sec_1_10 = sections.get("1.10", "")
    expected = project_input.technology.annual_waste_throughput if project_input else None

    val = _extract_first_number(sec_1_10)
    if val is not None and expected is not None:
        if abs(val - expected) > 0.5:
            report.flags.append(
                ConsistencyFlag(
                    section_a="1.10",
                    section_b="ProjectInput",
                    field_name="annual_waste_throughput",
                    value_a=val,
                    value_b=expected,
                    expected=expected,
                    tolerance=0.5,
                    severity="HIGH",
                    message=(
                        f"Section 1.10 waste throughput ({val:,.0f} tonnes) "
                        f"differs from ProjectInput ({expected:,.0f} tonnes)."
                    ),
                )
            )


def _check_capacity_consistency(
    sections: dict[str, str],
    project_input: ProjectInput | None,
    report: ConsistencyReport,
) -> None:
    sec_1_10 = sections.get("1.10", "")
    expected = project_input.technology.installed_capacity_mw if project_input else None

    if expected is not None:
        matches = re.findall(r"([\d,]+\.?\d*)\s*MW", sec_1_10, re.IGNORECASE)
        if matches:
            val = float(matches[0].replace(",", ""))
            if abs(val - expected) > 0.01:
                report.flags.append(
                    ConsistencyFlag(
                        section_a="1.10",
                        section_b="ProjectInput",
                        field_name="installed_capacity_mw",
                        value_a=val,
                        value_b=expected,
                        expected=expected,
                        tolerance=0.01,
                        severity="HIGH",
                        message=(
                            f"Section 1.10 capacity ({val} MW) differs from "
                            f"ProjectInput ({expected} MW)."
                        ),
                    )
                )


def _check_crediting_period_total(
    sections: dict[str, str],
    project_input: ProjectInput | None,
    report: ConsistencyReport,
) -> None:
    sec_4_4 = sections.get("4.4", "")
    if project_input is None:
        return

    net = project_input.quantification.net_emissions_tco2e_per_year
    years = project_input.dates.crediting_period_years
    expected_total = net * years
    actual_total = project_input.quantification.crediting_period_total_tco2e

    if abs(expected_total - actual_total) > 0.01:
        report.flags.append(
            ConsistencyFlag(
                section_a="4.4",
                section_b="ProjectInput",
                field_name="crediting_period_total_tco2e",
                value_a=actual_total,
                value_b=expected_total,
                expected=expected_total,
                tolerance=0.01,
                severity="HIGH",
                message=(
                    f"Crediting period total in ProjectInput ({actual_total:,.0f}) "
                    f"does not match calculation ({expected_total:,.0f} = {net:,.0f} × {years} years)."
                ),
            )
        )


def _check_baseline_project_emissions_relation(
    sections: dict[str, str],
    report: ConsistencyReport,
) -> None:
    baseline_text = sections.get("4.1", "")
    project_text = sections.get("4.2", "")
    net_text = sections.get("4.4", "")

    baseline_val = _extract_first_number(baseline_text)
    project_val = _extract_first_number(project_text)
    net_val = _extract_first_number(net_text)

    if baseline_val is not None and project_val is not None and net_val is not None:
        calculated_net = baseline_val - project_val
        if abs(calculated_net - net_val) > 0.1:
            report.flags.append(
                ConsistencyFlag(
                    section_a="4.1/4.2",
                    section_b="4.4",
                    field_name="net_calculation",
                    value_a=calculated_net,
                    value_b=net_val,
                    expected=calculated_net,
                    tolerance=0.1,
                    severity="CRITICAL",
                    message=(
                        f"Net tCO2e calculation error: Baseline ({baseline_val:,.0f}) "
                        f"- Project ({project_val:,.0f}) = {calculated_net:,.0f}, "
                        f"but Section 4.4 reports {net_val:,.0f}."
                    ),
                )
            )


def summarize_consistency_report(report: ConsistencyReport) -> dict[str, Any]:
    return {
        "run_id": report.run_id,
        "passed": report.passed,
        "critical_count": len(report.critical_flags),
        "high_count": len(report.high_flags),
        "critical_flags": [
            {"section_a": f.section_a, "section_b": f.section_b, "message": f.message}
            for f in report.critical_flags
        ],
        "high_flags": [
            {"section_a": f.section_a, "section_b": f.section_b, "message": f.message}
            for f in report.high_flags
        ],
    }
