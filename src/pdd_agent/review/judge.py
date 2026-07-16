"""LLM-judge machinery for VVB-style desk review of PDD draft sections.

The judge scores each DraftSection against `rules/verra/judge_rubric.yaml`.
For the default ``demo`` / ``noop`` providers it returns deterministic,
rule-based scores so no API keys are required. The provider-registry interface
is kept intact so a real LLM judge can be swapped in later by setting
``use_llm=True`` with an API-backed provider name.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
import yaml

from pdd_agent.llm.budget import TokenBudget
from pdd_agent.llm.provider import DraftRun, DraftSection, get_provider_registry

logger = structlog.get_logger()

_RUBRIC_PATH = Path(__file__).parent.parent.parent.parent / "rules" / "verra" / "judge_rubric.yaml"
_RUBRICS_DIR = _RUBRIC_PATH.parent / "rubrics"

_EVIDENCE_ID_RE = re.compile(r"\[E(\d{3})\]")

_QUANTITATIVE_SECTIONS = {"1.10", "4.1", "4.2", "4.4"}

_METHODOLOGY_FAMILY = {
    "ACM0022": "wte",
    "ACM0003": "wte",
    "VM0051": "rice",
    "VM0044": "biochar",
    "AMS-II.G": "cookstove",
}
_DEFAULT_FAMILY = "wte"


def _family_slug_for(methodology_ids: list[str] | None) -> str:
    """Resolve a methodology-family slug from a list of methodology IDs."""
    if not methodology_ids:
        return _DEFAULT_FAMILY
    normalized = str(methodology_ids[0]).strip().upper()
    return _METHODOLOGY_FAMILY.get(normalized, _DEFAULT_FAMILY)


# Judge model tiers (ASM-008): cheap tier for iteration, frontier tier for
# sign-off runs, chosen by provider. Override with PDD_JUDGE_MODEL.
_JUDGE_MODEL_TIER_DEFAULTS = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o-mini",
}

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class JudgeResult:
    """Scoring result for a single section."""

    section_key: str
    score: int  # 0-100
    passed: bool
    categories: dict[str, list[str]] = field(
        default_factory=lambda: {"critical": [], "advisory": []}
    )
    findings: list[dict[str, Any]] = field(default_factory=list)
    provider: str = "demo"
    model: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_key": self.section_key,
            "score": self.score,
            "passed": self.passed,
            "categories": self.categories,
            "findings": self.findings,
            "provider": self.provider,
            "model": self.model,
        }


class LLMJudge:
    """Score PDD draft sections against the VVB desk-review rubric.

    Args:
        provider_name: Provider to use when ``use_llm`` is enabled. Defaults to
            ``demo`` so no API keys are required.
        rubric_path: Override path to ``judge_rubric.yaml``.
        pass_threshold: Override pass threshold from the rubric.
        use_llm: If True, attempt to call the provider as an LLM judge. This is
            intentionally off by default until API-backed judge prompts are tuned.
        model_name: Override judge model name.
        methodology_ids: Project methodology IDs for family-aware rubric selection.
        token_budget: When given, attached to the judge's provider (if it
            supports ``set_budget``) so judge-call tokens are recorded in the
            same budget as drafting, instead of being excluded from run cost.
    """

    def __init__(
        self,
        provider_name: str = "demo",
        rubric_path: Path | None = None,
        pass_threshold: int | None = None,
        use_llm: bool = False,
        model_name: str | None = None,
        methodology_ids: list[str] | None = None,
        token_budget: TokenBudget | None = None,
    ) -> None:
        self.provider_name = provider_name
        self._methodology_ids = methodology_ids
        self.rubric_path = rubric_path or self._resolve_rubric_path(methodology_ids)
        self.rubric = self._load_rubric()
        self.pass_threshold = pass_threshold or int(self.rubric["scoring"]["pass_threshold"])
        self.use_llm = use_llm
        self.model_name = self._resolve_model_name(model_name, provider_name)
        self._criteria = {c["id"]: c for c in self.rubric["criteria"]}
        self._provider = get_provider_registry().get(provider_name)
        if token_budget is not None and hasattr(self._provider, "set_budget"):
            self._provider.set_budget(token_budget)
        self._quantitative_sections = self._resolve_quantitative_sections()

    @staticmethod
    def _resolve_model_name(model_name: str | None, provider_name: str) -> str | None:
        """Resolution order: explicit arg -> PDD_JUDGE_MODEL env -> tier default."""
        if model_name:
            return model_name
        env_model = os.environ.get("PDD_JUDGE_MODEL")
        if env_model:
            return env_model
        return _JUDGE_MODEL_TIER_DEFAULTS.get(provider_name)

    @staticmethod
    def _resolve_rubric_path(methodology_ids: list[str] | None) -> Path:
        """Select the family rubric file from methodology_ids, falling back to _RUBRIC_PATH."""
        family = _family_slug_for(methodology_ids)
        family_path = _RUBRICS_DIR / f"{family}.yaml"
        if family_path.exists():
            return family_path
        return _RUBRIC_PATH

    def _resolve_quantitative_sections(self) -> set[str]:
        """Read quantitative_sections from the loaded rubric, defaulting to the WTE set."""
        qs = self.rubric.get("quantitative_sections")
        if qs and isinstance(qs, list):
            return set(str(s) for s in qs)
        return set(_QUANTITATIVE_SECTIONS)

    def _load_rubric(self) -> dict[str, Any]:
        with open(self.rubric_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _weight(self, criterion_id: str) -> int:
        return int(self._criteria.get(criterion_id, {}).get("weight", 0))

    def judge_section(
        self,
        draft_section: DraftSection,
        project_input: Any | None = None,
        calc_result: Any | None = None,
    ) -> JudgeResult:
        """Judge a single draft section."""
        if self.use_llm and self.provider_name not in ("demo", "noop"):
            return self._llm_judge_section(draft_section, project_input, calc_result)

        return self._deterministic_judge_section(draft_section, project_input, calc_result)

    def judge_run(
        self,
        draft_run: DraftRun | dict[str, Any],
        project_input: Any | None = None,
        calc_result: Any | None = None,
    ) -> dict[str, JudgeResult]:
        """Judge every section in a DraftRun and return a map keyed by section key."""
        if isinstance(draft_run, dict):
            sections = draft_run.get("sections", [])
        else:
            sections = draft_run.sections

        results: dict[str, JudgeResult] = {}
        for section in sections:
            if isinstance(section, dict):
                section = DraftSection(**section)
            result = self.judge_section(section, project_input, calc_result)
            results[result.section_key] = result
        return results

    # ─────────────────────────────────────────────
    # Deterministic rubric-based judge (default)
    # ─────────────────────────────────────────────

    def _deterministic_judge_section(
        self,
        draft_section: DraftSection,
        project_input: Any | None,
        calc_result: Any | None,
    ) -> JudgeResult:
        text = draft_section.text or ""
        section_key = _section_key(draft_section)
        findings: list[dict[str, Any]] = []

        findings.extend(self._check_completeness(text, section_key))
        findings.extend(self._check_evidence_citations(text, project_input))
        findings.extend(self._check_methodology_conformance(text, draft_section))
        findings.extend(self._check_fabricated_facts(text, section_key, project_input, calc_result))
        findings.extend(
            self._check_marker_hygiene(
                text,
                section_key,
                draft_section.review_sensitivity,
            )
        )

        score = max(0, 100 - sum(f.get("deduction", 0) for f in findings))
        critical = [f for f in findings if f["category"] == "critical"]
        advisory = [f for f in findings if f["category"] == "advisory"]
        passed = score >= self.pass_threshold and not critical

        return JudgeResult(
            section_key=section_key,
            score=score,
            passed=passed,
            categories={
                "critical": [f["message"] for f in critical],
                "advisory": [f["message"] for f in advisory],
            },
            findings=findings,
            provider=self.provider_name,
        )

    def _add_finding(
        self,
        findings: list[dict[str, Any]],
        criterion_id: str,
        category: str,
        message: str,
    ) -> None:
        findings.append(
            {
                "criterion_id": criterion_id,
                "category": category,
                "message": message,
                "deduction": self._weight(criterion_id),
            }
        )

    def _check_completeness(self, text: str, section_key: str) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        if not text or len(text.strip()) < 30:
            self._add_finding(
                findings,
                "COMPLETENESS",
                "advisory",
                f"Section {section_key} appears too short or empty vs schema guidance.",
            )
        return findings

    def _check_evidence_citations(
        self, text: str, project_input: Any | None
    ) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        cited_ids = set(_EVIDENCE_ID_RE.findall(text))
        if not cited_ids:
            return findings

        registry = getattr(project_input, "evidence_registry", None) if project_input else None
        if registry is None:
            self._add_finding(
                findings,
                "EVIDENCE_CITATION_VALIDITY",
                "advisory",
                "Evidence citations found but no evidence registry is attached; cannot validate [E###] IDs.",
            )
            return findings

        valid_numbers = {
            re.search(r"\d+", item.evidence_id).group()
            for item in getattr(registry, "items", [])
            if item.evidence_id
        }
        invalid = sorted(cited_ids - valid_numbers)
        if invalid:
            self._add_finding(
                findings,
                "EVIDENCE_CITATION_VALIDITY",
                "critical",
                f"Cited evidence ID(s) not in registry: {', '.join(f'E{e}' for e in invalid)}.",
            )
        return findings

    def _check_methodology_conformance(
        self, text: str, draft_section: DraftSection
    ) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        content_class = getattr(draft_section, "content_class", "NARRATIVE")
        section_key = _section_key(draft_section)
        is_methodology_section = content_class in (
            "METHODOLOGY_DEPENDENT",
            "QUANTITATIVE",
        ) or section_key.startswith(("3.", "4.", "5.2"))

        if is_methodology_section:
            has_citation = any(
                marker in text for marker in ("[METHODOLOGY:", "[CALC:", "[E", "[CORPUS:")
            )
            if not has_citation:
                self._add_finding(
                    findings,
                    "METHODOLOGY_CONFORMANCE",
                    "advisory",
                    f"Section {section_key} is methodology/quantitative but lacks an explicit methodology, calc, or evidence citation.",
                )
        return findings

    def _check_fabricated_facts(
        self,
        text: str,
        section_key: str,
        project_input: Any | None,
        calc_result: Any | None,
    ) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        if section_key not in self._quantitative_sections:
            return findings

        expected = self._expected_quant_value(section_key, project_input, calc_result)
        if expected is None:
            return findings

        val = _extract_first_number(text)
        if val is None:
            return findings

        tolerance = max(0.01, abs(expected) * 0.001)
        if abs(val - expected) > tolerance:
            self._add_finding(
                findings,
                "NO_FABRICATED_FACTS",
                "critical",
                f"Section {section_key} reports {val:,.2f} but expected {expected:,.2f} (tolerance {tolerance:,.2f}).",
            )
        return findings

    def _expected_quant_value(
        self,
        section_key: str,
        project_input: Any | None,
        calc_result: Any | None,
    ) -> float | None:
        if project_input is None and calc_result is None:
            return None

        quant = getattr(project_input, "quantification", None) if project_input else None
        if section_key in ("1.10", "4.4"):
            if quant is not None:
                return getattr(quant, "net_emissions_tco2e_per_year", None)
            if calc_result is not None:
                return getattr(calc_result, "net_emission_reductions_tco2e", None)
        if section_key == "4.1":
            if quant is not None:
                return getattr(quant, "baseline_emissions_tco2e_per_year", None)
            if calc_result is not None:
                return getattr(calc_result, "baseline_emissions_tco2e", None)
        if section_key == "4.2":
            if quant is not None:
                return getattr(quant, "project_emissions_tco2e_per_year", None)
            if calc_result is not None:
                return getattr(calc_result, "project_emissions_tco2e", None)
        return None

    def _check_marker_hygiene(
        self,
        text: str,
        section_key: str,
        review_sensitivity: str,
    ) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        has_missing = "[MISSING]" in text
        has_review = "[REVIEW REQUIRED" in text
        has_inference = "[INFERENCE]" in text

        if has_missing:
            missing_category = "critical" if self._in_section_3_or_4(section_key) else "advisory"
            self._add_finding(
                findings,
                "MARKER_HYGIENE",
                missing_category,
                f"Section {section_key} contains unresolved [MISSING] markers.",
            )

        if has_review:
            review_category = "critical" if review_sensitivity == "CRITICAL" else "advisory"
            self._add_finding(
                findings,
                "MARKER_HYGIENE",
                review_category,
                f"Section {section_key} contains [REVIEW REQUIRED] markers.",
            )

        if has_inference:
            self._add_finding(
                findings,
                "MARKER_HYGIENE",
                "advisory",
                f"Section {section_key} contains [INFERENCE] markers.",
            )

        return findings

    @staticmethod
    def _in_section_3_or_4(section_key: str) -> bool:
        return section_key.startswith(("3", "4"))

    # ─────────────────────────────────────────────
    # LLM-backed judge interface (future path)
    # ─────────────────────────────────────────────

    def _llm_judge_section(
        self,
        draft_section: DraftSection,
        project_input: Any | None,
        calc_result: Any | None,
    ) -> JudgeResult:
        """Call the configured provider as a judge and parse structured findings.

        Expects the provider to return a JSON object with keys: score (0-100),
        passed (bool), critical (list of strings), advisory (list of strings).
        Tolerates markdown code fences around the JSON. Falls back to
        deterministic scoring on any provider error or unparseable response so
        the pipeline stays usable without a tuned judge prompt.
        """
        section_key = _section_key(draft_section)
        prompt = self._build_llm_judge_prompt(draft_section, project_input, calc_result)

        logger.info("llm_judge_section_start", section_key=section_key, provider=self.provider_name)
        try:
            response = self._provider.draft_section(
                section_id="judge",
                sub_section_id=section_key,
                prompt=prompt,
                provenance=["[JUDGE PROMPT]"],
            )
        except Exception as exc:
            logger.warning(
                "llm_judge_failed",
                section_key=section_key,
                error=str(exc),
                fallback="deterministic",
            )
            return self._deterministic_judge_section(draft_section, project_input, calc_result)

        payload = _parse_judge_json(response.text)
        if payload is None:
            score = self._extract_score(response.text)
            if score is None:
                logger.warning(
                    "llm_judge_unparseable",
                    section_key=section_key,
                    fallback="deterministic",
                )
                return self._deterministic_judge_section(draft_section, project_input, calc_result)
            passed = score >= self.pass_threshold
            return JudgeResult(
                section_key=section_key,
                score=score,
                passed=passed,
                categories={"critical": [], "advisory": []},
                findings=[],
                provider=self.provider_name,
                model=getattr(response, "model", None) or self.model_name,
            )

        score = int(payload.get("score", 0))
        critical = [str(item) for item in payload.get("critical", [])]
        advisory = [str(item) for item in payload.get("advisory", [])]
        passed = bool(payload.get("passed", score >= self.pass_threshold)) and not critical
        findings = [
            {"criterion_id": "LLM_JUDGE", "category": "critical", "message": m, "deduction": 0}
            for m in critical
        ] + [
            {"criterion_id": "LLM_JUDGE", "category": "advisory", "message": m, "deduction": 0}
            for m in advisory
        ]

        return JudgeResult(
            section_key=section_key,
            score=score,
            passed=passed,
            categories={"critical": critical, "advisory": advisory},
            findings=findings,
            provider=self.provider_name,
            model=getattr(response, "model", None) or self.model_name,
        )

    def _build_llm_judge_prompt(
        self,
        draft_section: DraftSection,
        project_input: Any | None,
        calc_result: Any | None,
    ) -> str:
        section_key = _section_key(draft_section)
        rubric_text = yaml.safe_dump(self.rubric, sort_keys=False)
        project_summary = ""
        if project_input is not None and hasattr(project_input, "summary"):
            project_summary = project_input.summary()

        calc_summary = ""
        if calc_result is not None:
            calc_summary = (
                f"Baseline: {getattr(calc_result, 'baseline_emissions_tco2e', 'N/A')}\n"
                f"Project:  {getattr(calc_result, 'project_emissions_tco2e', 'N/A')}\n"
                f"Leakage:  {getattr(calc_result, 'leakage_tco2e', 'N/A')}\n"
                f"Net:      {getattr(calc_result, 'net_emission_reductions_tco2e', 'N/A')}"
            )

        return (
            f"You are a VVB desk reviewer scoring PDD section {section_key}.\n\n"
            f"Rubric:\n{rubric_text}\n\n"
            f"Project summary:\n{project_summary}\n\n"
            f"Calc results:\n{calc_summary}\n\n"
            f"Draft section text:\n---\n{draft_section.text}\n---\n\n"
            "Return ONLY a JSON object with keys: score (0-100), passed (bool), "
            "critical (list of strings), advisory (list of strings)."
        )

    @staticmethod
    def _extract_score(text: str) -> int | None:
        match = re.search(r'"score"\s*:\s*(\d+)', text)
        if match:
            return int(match.group(1))
        match = re.search(r"score\s*[:=]\s*(\d+)", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None


def _parse_judge_json(text: str) -> dict[str, Any] | None:
    """Extract and parse the first JSON object found in judge response text.

    Tolerates markdown code fences and leading/trailing prose. Returns None
    when no valid JSON object with a "score" key is found.
    """
    if not text:
        return None
    match = _JSON_OBJECT_RE.search(text)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or "score" not in payload:
        return None
    return payload


def _section_key(draft_section: DraftSection) -> str:
    if draft_section.sub_section_id:
        return draft_section.sub_section_id
    return draft_section.section_id


def _extract_first_number(text: str) -> float | None:
    if not text:
        return None
    matches = re.findall(r"\d[\d,]*\.?\d*", text)
    if not matches:
        return None
    try:
        return float(matches[0].replace(",", ""))
    except ValueError:
        return None
