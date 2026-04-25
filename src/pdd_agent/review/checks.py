"""Rule-based review checks for drafted PDD sections.

Applies PRE/POST methodology checks, evidence attachment checks,
double-counting guards, and review-gate logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
import yaml

from pdd_agent.domain.methodology_rules import get_methodology_rules
from schemas.project_input import ProjectInput

logger = structlog.get_logger()

_RULES_PATH = (
    Path(__file__).parent.parent.parent.parent / "rules" / "verra" / "wte_review_rules.yaml"
)


@dataclass
class ReviewCheck:
    check_id: str
    severity: str
    description: str
    section_ref: str | None = None
    flag: bool = False
    message: str = ""


@dataclass
class ReviewCheckResult:
    run_id: str
    passed: bool
    checks: list[ReviewCheck] = field(default_factory=list)
    blocking_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    auto_approved_section_ids: list[str] = field(default_factory=list)

    def add_check(self, check: ReviewCheck) -> None:
        self.checks.append(check)
        if check.flag:
            if check.severity == "CRITICAL":
                self.blocking_issues.append(f"[{check.check_id}] {check.message}")
                self.passed = False
            else:
                self.warnings.append(f"[{check.check_id}] {check.message}")


def _load_review_rules() -> dict[str, Any]:
    with open(_RULES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _build_evidence_check(section_ref: str, evidence_type: str, section_text: str) -> ReviewCheck:
    has_evidence = bool(section_text and len(section_text) > 50)
    return ReviewCheck(
        check_id=f"EVIDENCE-{section_ref.replace('.', '-')}",
        severity="HIGH",
        description=f"Evidence required for {section_ref}: {evidence_type}",
        section_ref=section_ref,
        flag=not has_evidence,
        message=(
            f"Section {section_ref} appears to lack evidence attachment: {evidence_type}. "
            f"Add supporting documentation before this PDD can be validated."
        ),
    )


def run_review_checks(
    draft_run: Any,
    project_input: ProjectInput | None,
    run_id: str,
) -> ReviewCheckResult:
    """Run all review checks against a completed DraftRun.

    Args:
        draft_run: DraftRun instance from the orchestrator.
        project_input: ProjectInput (optional) for cross-reference checks.
        run_id: Run identifier for the result record.

    Returns:
        ReviewCheckResult with all check outcomes.
    """
    result = ReviewCheckResult(run_id=run_id, passed=True)
    rules = _load_review_rules()
    methodology_rules = get_methodology_rules()

    section_texts: dict[str, str] = {}
    for s in draft_run.sections:
        key = f"{s.section_id}.{s.sub_section_id}" if s.sub_section_id else s.section_id
        section_texts[key] = s.text

    for check_def in rules.get("double_counting_guards", []):
        guard = _run_double_counting_guard(check_def, project_input, section_texts)
        result.add_check(guard)

    for check_def in rules.get("quantitative_cross_references", []):
        check = _run_quantitative_check(check_def, project_input, section_texts)
        result.add_check(check)

    for evidence_def in rules.get("evidence_requirements", []):
        sec_ref = evidence_def["section_ref"]
        text = section_texts.get(sec_ref, "")
        check = _build_evidence_check(sec_ref, evidence_def["evidence_type"], text)
        result.add_check(check)

    for s in draft_run.sections:
        section_ref = f"{s.section_id}.{s.sub_section_id}" if s.sub_section_id else s.section_id
        synthetic_uses = getattr(s, "synthetic_uses", []) or []
        review_sensitivity = getattr(s, "review_sensitivity", "LOW")
        blocked = [item for item in synthetic_uses if item.get("blocked_review")]
        if blocked and review_sensitivity in {"HIGH", "CRITICAL"}:
            result.add_check(
                ReviewCheck(
                    check_id=f"ASSUMPTION-BLOCK-{section_ref.replace('.', '-')}",
                    severity="CRITICAL" if review_sensitivity == "CRITICAL" else "HIGH",
                    description="Blocked synthetic assumption in sensitive section",
                    section_ref=section_ref,
                    flag=True,
                    message=(
                        f"Section {section_ref} depends on review-gated synthetic inputs: "
                        + ", ".join(item.get("field_path", "unknown") for item in blocked)
                    ),
                )
            )
        elif synthetic_uses and review_sensitivity in {"HIGH", "CRITICAL"}:
            result.add_check(
                ReviewCheck(
                    check_id=f"ASSUMPTION-WARN-{section_ref.replace('.', '-')}",
                    severity="HIGH",
                    description="Synthetic assumptions affect a sensitive section",
                    section_ref=section_ref,
                    flag=True,
                    message=(
                        f"Section {section_ref} uses {len(synthetic_uses)} synthetic/demo-backed field(s) and must remain review-gated."
                    ),
                )
            )

    if project_input:
        rules_engine = get_methodology_rules()
        post_results = rules_engine.run_post_draft_checks(section_texts)
        for pr in post_results:
            check = ReviewCheck(
                check_id=pr.get("check_id", "POST-UNKNOWN"),
                severity=pr.get("severity", "HIGH"),
                description=pr.get("description", ""),
                flag=pr.get("failed", False),
                message=pr.get("message", pr.get("description", "")),
            )
            result.add_check(check)

    for section_def in rules.get("auto_approval_candidates", []):
        sid = section_def["section_id"]
        ssid = section_def["sub_section_id"]
        key = f"{sid}.{ssid}"
        draft = next(
            (s for s in draft_run.sections if f"{s.section_id}.{s.sub_section_id}" == key),
            None,
        )
        if (
            draft
            and draft.confidence == "HIGH"
            and not any(c.flag and c.section_ref == key for c in result.checks)
        ):
            result.auto_approved_section_ids.append(key)

    blocking = [c for c in result.checks if c.flag and c.severity == "CRITICAL"]
    result.passed = len(blocking) == 0

    if blocking:
        logger.warning(
            "review_checks_failed",
            run_id=run_id,
            blocking_count=len(blocking),
            issues=[c.message for c in blocking],
        )
    else:
        logger.info(
            "review_checks_passed",
            run_id=run_id,
            auto_approved=len(result.auto_approved_section_ids),
        )

    return result


def _run_double_counting_guard(
    guard_def: dict[str, Any],
    project_input: ProjectInput | None,
    section_texts: dict[str, str],
) -> ReviewCheck:
    guard_id = guard_def.get("guard_id", "DC-UNKNOWN")
    desc = guard_def.get("description", "")
    trigger = guard_def.get("trigger_condition", "")
    blocking = guard_def.get("blocking", False)

    flag = False
    message = ""

    if project_input is None:
        flag = True
        message = (
            f"{guard_id}: ProjectInput not provided — cannot verify double-counting guard: {desc}"
        )
    elif guard_id == "DC-01":
        tech = project_input.technology
        if tech.landfill_diversion_claim and tech.fuel_substitution_claim:
            sec_1_16 = section_texts.get("1.16", "")
            if "credit allocation" not in sec_1_16.lower() and "allocation" not in sec_1_16.lower():
                flag = True
                message = (
                    f"{guard_id} CRITICAL: Project claims BOTH landfill diversion and fuel "
                    f"substitution. Section 1.16 must contain an explicit credit allocation "
                    f"table. Without this, validation will fail."
                )
    elif guard_id == "DC-02":
        if project_input.technology.installed_capacity_mw > 0:
            sec_1_15 = section_texts.get("1.15", "")
            if (
                "rec" not in sec_1_15.lower()
                and "renewable energy certificate" not in sec_1_15.lower()
            ):
                flag = True
                message = (
                    f"{guard_id} CRITICAL: Section 1.15 does not address RECs. "
                    f"If RECs are sold, the grid emission factor must be adjusted."
                )
    elif guard_id == "DC-03":
        if project_input.technology.landfill_diversion_claim:
            sec_4_3 = section_texts.get("4.3", "")
            if "waste-shift" not in sec_4_3.lower() and "waste shifting" not in sec_4_3.lower():
                flag = True
                message = (
                    f"{guard_id}: Section 4.3 leakage assessment does not address "
                    f"waste-shifting risk. Add evidence that diverted waste was "
                    f"previously destined for landfill."
                )
    elif guard_id == "DC-04":
        if project_input:
            gef_source = project_input.quantification.grid_emission_factor_source.lower()
            approved = any(
                kw in gef_source
                for kw in ["acm0022 default", "national grid", "regional grid", "grid authority"]
            )
            if not approved:
                flag = True
                message = (
                    f"{guard_id} CRITICAL: Grid emission factor source is not from an "
                    f"approved methodology source. Use ACM0022 default or official "
                    f"national/regional grid authority."
                )

    return ReviewCheck(
        check_id=guard_id,
        severity="CRITICAL" if blocking else "HIGH",
        description=desc,
        flag=flag,
        message=message,
    )


def _run_quantitative_check(
    check_def: dict[str, Any],
    project_input: ProjectInput | None,
    section_texts: dict[str, str],
) -> ReviewCheck:
    check_id = check_def.get("check", "QUANT-UNKNOWN")
    desc = check_def.get("description", "")
    severity = check_def.get("severity", "HIGH")
    tolerance = check_def.get("tolerance", 0.01)

    flag = False
    message = ""

    if project_input is None:
        flag = True
        message = (
            f"{check_id}: Cannot verify quantitative cross-reference: ProjectInput not provided"
        )

    elif check_id == "section_1_10_matches_section_4_4":
        sec_1_10 = section_texts.get("1.10", "")
        sec_4_4 = section_texts.get("4.4", "")
        net_input = project_input.quantification.net_emissions_tco2e_per_year
        import re

        numbers_1_10 = re.findall(r"[\d,]+\.?\d*", sec_1_10)
        numbers_4_4 = re.findall(r"[\d,]+\.?\d*", sec_4_4)

        if numbers_1_10 and numbers_4_4:
            val_1_10 = float(numbers_1_10[0].replace(",", ""))
            val_4_4 = float(numbers_4_4[0].replace(",", ""))
            if abs(val_1_10 - net_input) > tolerance and abs(val_4_4 - net_input) > tolerance:
                flag = True
                message = (
                    f"{check_id} CRITICAL: Section 1.10 and Section 4.4 net tCO2e values "
                    f"do not match ProjectInput value ({net_input:,.0f}). "
                    f"Values found: 1.10={val_1_10:,.0f}, 4.4={val_4_4:,.0f}"
                )

    elif check_id == "crediting_period_total_consistency":
        net = project_input.quantification.net_emissions_tco2e_per_year
        years = project_input.dates.crediting_period_years
        expected_total = net * years
        actual_total = project_input.quantification.crediting_period_total_tco2e
        if abs(expected_total - actual_total) > tolerance:
            flag = True
            message = (
                f"{check_id} CRITICAL: Crediting period total tCO2e mismatch. "
                f"Expected {expected_total:,.0f} (= {net:,.0f} × {years} years), "
                f"got {actual_total:,.0f} in ProjectInput."
            )

    return ReviewCheck(
        check_id=check_id,
        severity=severity,
        description=desc,
        flag=flag,
        message=message,
    )


def summarize_review_result(result: ReviewCheckResult) -> dict[str, Any]:
    return {
        "run_id": result.run_id,
        "passed": result.passed,
        "blocking_issues": result.blocking_issues,
        "warnings": result.warnings,
        "auto_approved_sections": result.auto_approved_section_ids,
        "total_checks": len(result.checks),
    }
