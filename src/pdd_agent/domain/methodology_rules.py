"""Python wrapper for the Verra WTE methodology rules YAML.

Provides a typed interface to all rule lookups, compliance checks,
and parameter references defined in `rules/verra/wte_methodology_rules.yaml`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()


class MethodologyRules:
    """Loader and accessor for the WTE methodology rules document."""

    def __init__(self, rules_path: Path | None = None) -> None:
        if rules_path is None:
            rules_path = (
                Path(__file__).parent.parent.parent.parent
                / "rules"
                / "verra"
                / "wte_methodology_rules.yaml"
            )
        self._path = Path(rules_path)
        self._raw = self._load()
        self._methodologies: dict[str, Any] = self._raw.get("methodologies", {})
        self._safeguards: dict[str, Any] = self._raw.get("safeguards", {})
        self._compliance: dict[str, Any] = self._raw.get("compliance_checks", {})
        self._double_counting: dict[str, Any] = self._raw.get("double_counting_prevention", {})

    def _load(self) -> dict[str, Any]:
        with open(self._path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def version(self) -> str:
        return self._raw.get("version", "unknown")

    @property
    def bucket(self) -> str:
        return self._raw.get("bucket", "unknown")

    def methodology(self, mid: str) -> dict[str, Any] | None:
        return self._methodologies.get(mid)

    def applicability_conditions(self, mid: str) -> list[dict[str, Any]]:
        meth = self._methodology(mid)
        return meth.get("applicability_conditions", []) if meth else []

    def _methodology(self, mid: str) -> dict[str, Any] | None:
        return self._methodologies.get(mid)

    def double_counting_risks(self, mid: str) -> list[dict[str, Any]]:
        meth = self._methodology(mid)
        return meth.get("double_counting_risks", []) if meth else []

    def additionality_rules(self, mid: str) -> list[dict[str, Any]]:
        meth = self._methodology(mid)
        return meth.get("additionality_rules", []) if meth else []

    def parameters(self, mid: str) -> list[dict[str, Any]]:
        meth = self._methodology(mid)
        return meth.get("parameters", []) if meth else []

    def wte_safeguards(self) -> list[dict[str, Any]]:
        return self._safeguards.get("wte_specific", [])

    def pre_draft_checks(self) -> list[dict[str, Any]]:
        return self._compliance.get("pre_draft", [])

    def post_draft_checks(self) -> list[dict[str, Any]]:
        return self._compliance.get("post_draft", [])

    def double_counting_boundaries(self) -> list[dict[str, Any]]:
        return self._double_counting.get("boundaries", [])

    def run_pre_draft_checks(self, project_input: Any) -> list[dict[str, Any]]:
        """Run all pre-draft compliance checks against a ProjectInput instance.

        Returns a list of failed checks with check_id, description, and severity.
        """
        failures: list[dict[str, Any]] = []
        tech = project_input.technology
        quant = project_input.quantification
        comp = project_input.compliance_and_ownership

        for check in self.pre_draft_checks():
            cid = check["check_id"]
            severity = check["severity"]
            desc = check["description"]
            applies = check.get("applies_to", [])

            if applies and not any(m in tech.methodology_ids for m in applies):
                continue

            passed = True
            reason = ""

            if cid == "PRE-001":
                if tech.landfill_diversion_claim and tech.fuel_substitution_claim:
                    passed = False
                    reason = "Project claims BOTH landfill diversion and fuel substitution without explicit credit allocation."

            elif cid == "PRE-002":
                src = quant.grid_emission_factor_source.lower()
                official_sources = ["official", "national", "ACM0022 default", "verra"]
                if not any(s in src for s in official_sources):
                    passed = False
                    reason = f"Grid emission factor source '{quant.grid_emission_factor_source}' does not appear official."

            elif cid == "PRE-003":
                if "ACM0022" in tech.methodology_ids:
                    if quant.baseline_emissions_tco2e_per_year <= 0:
                        passed = False
                        reason = "Baseline emissions must be > 0 for ACM0022 projects."

            elif cid == "PRE-004":
                required_params = {"annual_waste_throughput", "grid_emission_factor"}
                provided = {
                    p["name"].lower().replace(" ", "_") for p in quant.model_dump().keys() if p
                }
                missing = required_params - provided
                if missing and "ACM0022" in tech.methodology_ids:
                    passed = False
                    reason = f"Monitoring parameters may be incomplete: {missing}"

            if not passed:
                failures.append(
                    {
                        "check_id": cid,
                        "severity": severity,
                        "description": desc,
                        "reason": reason,
                    }
                )

        return failures

    def run_post_draft_checks(self, pdd_sections: dict[str, Any]) -> list[dict[str, Any]]:
        """Run post-draft compliance checks against a drafted PDD section dict.

        pdd_sections: dict mapping canonical section_id -> section text content.
        Returns list of failed checks.
        """
        failures: list[dict[str, Any]] = []

        for check in self.post_draft_checks():
            cid = check["check_id"]
            severity = check["severity"]
            desc = check["description"]
            applies = check.get("applies_to", [])

            passed = True
            reason = ""

            if cid == "POST-001":
                s1_10 = pdd_sections.get("1.10", "")
                s4_4 = pdd_sections.get("4.4", "")
                if s1_10 and s4_4:
                    import re

                    nums_1_10 = re.findall(r"[\d,]+\.?\d*", s1_10)
                    nums_4_4 = re.findall(r"[\d,]+\.?\d*", s4_4)
                    if nums_1_10 and nums_4_4 and nums_1_10[-1] != nums_4_4[-1]:
                        passed = False
                        reason = "Section 1.10 tCO2e estimate does not match Section 4.4 net calculation."

            elif cid == "POST-002":
                s3_2 = pdd_sections.get("3.2", "")
                if s3_2:
                    yes_no_markers = [
                        "yes",
                        "no",
                        "meets",
                        "not meet",
                        "applicable",
                        "not applicable",
                    ]
                    if not any(m in s3_2.lower() for m in yes_no_markers):
                        passed = False
                        reason = (
                            "Section 3.2 applicability conditions not individually checked YES/NO."
                        )

            elif cid == "POST-003":
                citation_markers = [
                    "source:",
                    "reference:",
                    "evidence:",
                    "cited:",
                    "attach",
                    "see section",
                ]
                high_review_sections = ["3.4", "3.5", "4.1", "4.2", "4.3"]
                for sid in high_review_sections:
                    text = pdd_sections.get(sid, "")
                    if text and not any(m in text.lower() for m in citation_markers):
                        passed = False
                        reason = f"Section {sid} (HIGH_REVIEW) lacks cited sources or evidence references."
                        break

            elif cid == "POST-004":
                s1_16 = pdd_sections.get("1.16", "")
                if s1_16:
                    rec_keywords = [
                        "rec",
                        "renewable energy certificate",
                        "renewable attribute",
                        "power purchase agreement",
                    ]
                    elec_keywords = ["electricity", "electricity generated", "energy generated"]
                    has_elec = any(k in s1_16.lower() for k in elec_keywords)
                    has_rec = any(k in s1_16.lower() for k in rec_keywords)
                    if has_elec and not has_rec:
                        passed = False
                        reason = "Section 1.16 mentions electricity but does not address RECs."

            if not passed:
                failures.append(
                    {
                        "check_id": cid,
                        "severity": severity,
                        "description": desc,
                        "reason": reason,
                    }
                )

        return failures


_methodology_rules: MethodologyRules | None = None


def get_methodology_rules() -> MethodologyRules:
    global _methodology_rules
    if _methodology_rules is None:
        _methodology_rules = MethodologyRules()
    return _methodology_rules
