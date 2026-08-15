"""Per-section planner and executor for PDD drafting.

Coordinates retrieval, prompt assembly, and LLM calls for each canonical
section. Enforces review gates and converts unsupported claims to TODOs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import structlog
import yaml

from pdd_agent.domain.methodology_rules import get_methodology_rules
from pdd_agent.llm.budget import TokenBudget, BudgetExhaustedError
from pdd_agent.llm.judge_selection import resolve_judge_provider
from pdd_agent.llm.provider import (
    BaseProvider,
    DraftRun,
    DraftSection,
    NoopProvider,
)
from pdd_agent.phase06.assumptions import (
    output_ref_for_section,
    relevant_fact_entries,
    synthetic_entries,
    write_assumption_burden_report,
)
from pdd_agent.retrieval.search import (
    get_examples_for_section,
    get_section_heading_examples,
)
from pdd_agent.review.checks import run_review_checks, summarize_review_result
from pdd_agent.review.consistency import (
    check_quantitative_consistency,
    summarize_consistency_report,
)
from pdd_agent.review.judge import LLMJudge
from pdd_agent.review.states import init_review_state, ReviewState
from pdd_agent.review.tbd_tracker import TBDTracker
from schemas.project_input import ProjectInput

logger = structlog.get_logger()

_PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "prompts"
_SCHEMA_PATH = Path(__file__).parent.parent.parent.parent / "schemas" / "pdd_section_schema.yaml"

# Maps a project's primary methodology ID to the prompt-overlay / rubric
# family slug. Unknown or absent methodology IDs default to "wte" for
# backward compatibility with every project drafted before methodology
# families existed.
_METHODOLOGY_FAMILY = {
    "ACM0022": "wte",
    "ACM0003": "wte",
    "VM0051": "rice",
    "VM0044": "biochar",
    "AMS-II.G": "cookstove",
}
_DEFAULT_FAMILY = "wte"


def family_slug_for(methodology_ids: Sequence[str] | None) -> str:
    """Resolve a methodology-family slug from a project's methodology IDs.

    Uses the first methodology ID, normalized to uppercase. Falls back to
    "wte" when methodology_ids is empty, None, or unrecognized.
    """
    if not methodology_ids:
        return _DEFAULT_FAMILY
    normalized = str(methodology_ids[0]).strip().upper()
    return _METHODOLOGY_FAMILY.get(normalized, _DEFAULT_FAMILY)


# Domain descriptor substituted into the shared system-prompt template below,
# keyed by the same family slug family_slug_for() resolves. The "wte" entry
# must stay exactly "waste-to-energy projects" — every real provider hardcoded
# this system prompt verbatim before system_prompt_for() existed, and WTE
# drafting behavior must stay byte-identical.
_FAMILY_SYSTEM_DESCRIPTOR = {
    "wte": "waste-to-energy projects",
    "rice": "rice cultivation (alternate wetting and drying) projects",
    "biochar": "biochar carbon-removal projects",
    "cookstove": "improved cookstove projects",
}


def system_prompt_for(methodology_ids: Sequence[str] | None) -> str:
    """Return the family-aware system prompt for the given methodology IDs.

    Resolves the family via family_slug_for (first ID, uppercase-normalized;
    unknown/empty/None defaults to "wte"), then substitutes that family's
    domain descriptor into the shared template. The wte case is byte-
    identical to the string every real provider (OpenAI, Anthropic, Ollama)
    hardcoded before this function existed.
    """
    family = family_slug_for(methodology_ids)
    descriptor = _FAMILY_SYSTEM_DESCRIPTOR.get(family, _FAMILY_SYSTEM_DESCRIPTOR[_DEFAULT_FAMILY])
    return (
        "You are a technical writing assistant specializing in Verra VCS "
        f"carbon credit Project Design Documents for {descriptor}. "
        "Follow the prompt instructions exactly. Cite all sources using the "
        "required citation format. Never fabricate data."
    )


class SectionOrchestrator:
    """Orchestrates section-level retrieval, prompt assembly, and drafting."""

    def __init__(
        self,
        provider: BaseProvider | None = None,
        project_input: ProjectInput | None = None,
        run_id: str | None = None,
        schema_path: Path | None = None,
        prompts_dir: Path | None = None,
        calc_result: Any | None = None,
        token_budget: TokenBudget | None = None,
        enable_judge: bool = False,
        max_redraft_attempts: int = 3,
        assumption_burden_path: Path | str | None = None,
        runs_dir: Path | str | None = None,
    ) -> None:
        self._provider = provider or NoopProvider()
        self._assumption_burden_path = assumption_burden_path
        self._runs_dir = Path(runs_dir) if runs_dir is not None else None
        self._project = project_input
        self._schema_path = schema_path or _SCHEMA_PATH
        self._prompts_dir = prompts_dir or _PROMPTS_DIR
        self._schema = self._load_schema()
        self._methodology_rules = get_methodology_rules()
        self._run_id = (
            run_id or f"run-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6]}"
        )
        self._run = DraftRun(
            run_id=self._run_id,
            project_name=project_input.project.project_name if project_input else "unknown",
            provider=getattr(self._provider, "name", "noop"),
        )
        self._drafted: dict[str, DraftSection] = {}
        self._calc_result = calc_result
        self._budget = token_budget or self._default_budget()
        self._use_v2_prompt = self._should_use_v2()
        self._enable_judge = enable_judge
        self._max_redraft_attempts = max(0, max_redraft_attempts)
        self.redraft_count: int = 0
        self._judge_provider_cache: tuple[str, bool] | None = None

        if hasattr(self._provider, "set_budget"):
            self._provider.set_budget(self._budget)
        if hasattr(self._provider, "set_project_input"):
            self._provider.set_project_input(self._project)
        if hasattr(self._provider, "set_system_prompt"):
            self._provider.set_system_prompt(
                system_prompt_for(
                    self._project.technology.methodology_ids if self._project else None
                )
            )

    def _family_slug(self) -> str:
        """Resolve this project's methodology-family slug (see family_slug_for)."""
        if not self._project:
            return _DEFAULT_FAMILY
        return family_slug_for(self._project.technology.methodology_ids)

    def _load_overlay(self) -> str:
        """Return the domain-framing overlay Markdown for this project's family.

        Falls back to the WTE overlay when the family-specific file is
        missing, so drafting never breaks on an incomplete overlay set.
        """
        family = self._family_slug()
        overlay_path = self._prompts_dir / "methodologies" / f"{family}.md"
        if not overlay_path.exists():
            overlay_path = self._prompts_dir / "methodologies" / f"{_DEFAULT_FAMILY}.md"
        try:
            return overlay_path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def _default_budget(self) -> TokenBudget:
        import os

        max_tokens = os.environ.get("PDD_MAX_TOKENS")
        max_cost = os.environ.get("PDD_MAX_COST_USD")
        kwargs: dict[str, Any] = {}
        if max_tokens:
            try:
                kwargs["max_tokens"] = int(max_tokens)
            except ValueError:
                logger.warning("invalid_pdd_max_tokens", value=max_tokens)
        if max_cost:
            try:
                kwargs["max_cost_usd"] = float(max_cost)
            except ValueError:
                logger.warning("invalid_pdd_max_cost_usd", value=max_cost)
        return TokenBudget(**kwargs)

    def _is_demo_run(self) -> bool:
        return getattr(self._provider, "name", "") == "demo"

    def _should_use_v2(self) -> bool:
        if self._project and self._project.generation_controls:
            return self._project.generation_controls.use_v2_prompt
        return getattr(self._provider, "name", "") not in ("noop", "demo")

    def _max_corpus_examples(self) -> int:
        if self._project and self._project.generation_controls:
            return self._project.generation_controls.max_corpus_examples
        return 5

    def _max_corpus_chars(self) -> int:
        if self._project and self._project.generation_controls:
            return self._project.generation_controls.max_corpus_chars
        return 1500

    def _should_inject_calc(self) -> bool:
        if self._calc_result is None:
            return False
        if self._project and self._project.generation_controls:
            return self._project.generation_controls.inject_calc_results
        return True

    def _should_inject_retrieval(self) -> bool:
        if self._project and self._project.generation_controls:
            return self._project.generation_controls.inject_corpus_retrieval
        return True

    def _is_quantification_section(self, section_id: str, sub_section_id: str | None) -> bool:
        if section_id in ("1", "4"):
            return True
        ssid = sub_section_id or ""
        return ssid.startswith("1.") or ssid.startswith("4.")

    def _calc_is_authoritative(self) -> bool:
        """Whether calc scalars override ProjectInput.quantification for prompt facts.

        Read at call time (not cached), matching the rest of the module's
        environment-variable convention, so tests can monkeypatch it freely.
        """
        import os

        return os.environ.get("PDD_CALC_AUTHORITATIVE") == "1"

    def _build_structured_content(self, section_key: str) -> dict[str, Any] | None:
        """The structured_content payload for a table-bearing section.

        PHASE-03 (2026-08-13 grounding-rebuild plan): now that the exporter
        renders prose *and* table together instead of the table replacing the
        prose, this method was widened from the two calc-native sections
        ("4.4", "5.2") to also cover "1.5" (proponent), "3.2"
        (applicability), "3.3" (ghg_boundary), and "5.1"
        (monitoring_fixed_params). Returns None for every other section key,
        and whenever the data a given key needs is absent.
        """
        if section_key == "4.4":
            return self._structured_emissions_summary()
        if section_key == "5.2":
            return self._structured_monitoring_tracked_params()
        if section_key == "1.5":
            return self._structured_proponent()
        if section_key == "3.2":
            return self._structured_applicability()
        if section_key == "3.3":
            return self._structured_ghg_boundary()
        if section_key == "5.1":
            return self._structured_monitoring_fixed_params()
        return None

    def _structured_emissions_summary(self) -> dict[str, Any] | None:
        if not self._calc_result:
            return None
        schedule = getattr(self._calc_result, "annual_schedule", [])
        if not schedule:
            return None
        entries = [{"period": e.year, "value": f"{e.net_tco2e:,.0f}"} for e in schedule]
        total = sum(e.net_tco2e for e in schedule)
        return {
            "table_type": "emissions_summary",
            "data": {"entries": entries, "total": f"{total:,.0f}"},
        }

    def _structured_monitoring_tracked_params(self) -> dict[str, Any] | None:
        if not self._calc_result:
            return None
        params = getattr(self._calc_result, "monitoring_params", [])
        tracked = [p for p in params if p.get("section_ref") == "5.2"]
        if not tracked:
            return None
        entries = [
            {
                "parameter": p.get("name", ""),
                "unit": p.get("unit", ""),
                "description": p.get("name", ""),
                "frequency": p.get("frequency", ""),
                "equipment": p.get("source", ""),
                "qa_qc": "Per methodology monitoring plan",
            }
            for p in tracked
        ]
        return {"table_type": "monitoring_tracked_params", "data": {"entries": entries}}

    def _structured_monitoring_fixed_params(self) -> dict[str, Any] | None:
        if not self._calc_result:
            return None
        params = getattr(self._calc_result, "monitoring_params", [])
        fixed = [p for p in params if p.get("section_ref") != "5.2"]
        if not fixed:
            return None
        entries = []
        for p in fixed:
            value = "-"
            if p.get("id") == "ACM0022-PARAM-04" and self._project is not None:
                gef = self._project.quantification.grid_emission_factor
                if gef is not None:
                    value = str(gef)
            entries.append(
                {
                    "parameter": p.get("name", ""),
                    "unit": p.get("unit", ""),
                    "description": p.get("name", ""),
                    "value": value,
                    "source": p.get("source", ""),
                    "comments": "Fixed at validation",
                }
            )
        return {"table_type": "monitoring_fixed_params", "data": {"entries": entries}}

    def _primary_methodology_id(self) -> str | None:
        if not self._project or not self._project.technology.methodology_ids:
            return None
        return self._project.technology.methodology_ids[0]

    def _structured_proponent(self) -> dict[str, Any] | None:
        if not self._project:
            return None
        p = self._project
        address = f"{p.location.city}, {p.location.region}, {p.location.country}"
        return {
            "table_type": "proponent",
            "data": {
                "org_name": p.project.proponent_name,
                "contact_name": "-",
                "title": "-",
                "address": address,
                "telephone": "-",
                "email": p.project.proponent_contact_email,
            },
        }

    def _structured_applicability(self) -> dict[str, Any] | None:
        mid = self._primary_methodology_id()
        if not mid:
            return None
        conditions = self._methodology_rules.applicability_conditions(mid)
        if not conditions:
            return None
        checklist = self._project.methodology_applicability.eligibility_checklist
        entries = []
        for condition in conditions:
            checked = checklist.get(condition.get("id", ""))
            if checked is True:
                justification = "Confirmed"
            elif checked is False:
                justification = "Not confirmed — see Section 3.6"
            else:
                justification = "Not assessed"
            entries.append(
                {
                    "methodology": mid,
                    "condition": condition.get("text", ""),
                    "justification": justification,
                }
            )
        return {"table_type": "applicability", "data": {"entries": entries}}

    def _structured_ghg_boundary(self) -> dict[str, Any] | None:
        mid = self._primary_methodology_id()
        if not mid:
            return None
        rows = self._methodology_rules.ghg_boundary(mid)
        if not rows:
            return None
        entries = [
            {
                "scenario": row.get("scenario", ""),
                "source": row.get("source", ""),
                "gas": row.get("gas", ""),
                "included": "Yes" if row.get("included") else "No",
                "justification": row.get("justification", ""),
            }
            for row in rows
        ]
        return {"table_type": "ghg_boundary", "data": {"entries": entries}}

    def _format_calc_injection(self) -> str:
        """Format calc results for injection into Section 4 prompts.

        Three-branch dispatch:
        1. No calc result -> empty string.
        2. PddCalcResult with non-ACM0022 methodology -> to_prompt_block().
        3. ACM0022 (raw or via PddCalcResult.raw_result) -> existing WTE format.
        """
        if not self._calc_result:
            return ""

        cr = self._calc_result
        from pdd_agent.calc.dispatch import PddCalcResult

        if isinstance(cr, PddCalcResult) and cr.methodology_id != "ACM0022":
            return cr.to_prompt_block()

        raw = getattr(cr, "raw_result", None)
        if isinstance(raw, PddCalcResult) and raw.methodology_id != "ACM0022":
            return raw.to_prompt_block()

        if not isinstance(cr, PddCalcResult):
            raw = cr
        else:
            raw = getattr(cr, "raw_result", None) or cr
        methodology_name = (
            self._project.technology.methodology_ids[0]
            if self._project and self._project.technology.methodology_ids
            else "ACM0022"
        )
        parts = [
            f"\n## {methodology_name} Calculation Engine Results\n",
            f"The following values were computed by the {methodology_name} pure-Python calculation engine.\n"
            "Use these as the authoritative quantification values. Cite with `[CALC: component_name]`.\n",
            f"- **Baseline emissions**: {raw.baseline_emissions_tco2e:,.2f} tCO2e/year [CALC: baseline_total]",
            f"  - BE_CH4 (methane from SWDS): {raw.baseline_methane_swds_tco2e:,.2f} tCO2e/year [CALC: BE_CH4]",
            f"  - BE_EC (displaced grid electricity): {raw.baseline_electricity_tco2e:,.2f} tCO2e/year [CALC: BE_EC]",
            f"- **Project emissions**: {raw.project_emissions_tco2e:,.2f} tCO2e/year [CALC: project_total]",
            f"  - PE_EC (grid consumption): {raw.project_electricity_consumption_tco2e:,.2f} tCO2e/year [CALC: PE_EC]",
            f"  - PE_FC (fossil fuel): {raw.project_fossil_fuel_tco2e:,.2f} tCO2e/year [CALC: PE_FC]",
            f"  - PE_CH4 (AD leakage): {raw.project_methane_leakage_tco2e:,.2f} tCO2e/year [CALC: PE_CH4]",
            f"  - PE_FLARE (flare): {raw.project_flaring_tco2e:,.2f} tCO2e/year [CALC: PE_FLARE]",
            f"- **Leakage**: {raw.leakage_tco2e:,.2f} tCO2e/year [CALC: leakage_total]",
            f"  - LE_RDF (RDF combustion): {raw.leakage_rdf_combustion_tco2e:,.2f} tCO2e/year [CALC: LE_RDF]",
            f"  - LE_AD (digestate): {raw.leakage_digestate_tco2e:,.2f} tCO2e/year [CALC: LE_AD]",
            f"- **Net emission reductions**: {raw.net_emission_reductions_tco2e:,.2f} tCO2e/year [CALC: net_ER]",
            f"- **Crediting period total**: {raw.crediting_period_total_tco2e:,.2f} tCO2e ({raw.crediting_period_years} years) [CALC: crediting_total]",
            "",
            "### Key Intermediates",
            f"- Organic waste to AD: {raw.organic_waste_to_ad_tonnes:,.1f} tonnes/year",
            f"- Annual biogas: {raw.annual_biogas_m3:,.0f} Nm3/year",
            f"- Annual methane: {raw.annual_methane_m3:,.0f} Nm3/year ({raw.annual_methane_tonnes:,.1f} tonnes)",
            f"- Electricity generated: {raw.electricity_generated_mwh:,.1f} MWh/year",
            f"- Methodology: {raw.methodology_version}",
            "",
        ]
        return "\n".join(parts)

    def _format_retrieval_results(
        self, examples: Sequence[Any], max_examples: int, max_chars: int
    ) -> str:
        """Format corpus retrieval results with BM25 scores for prompt injection."""
        if not examples:
            return "\n## Corpus Examples: NONE — human review required.\n"

        parts = ["\n## Corpus Evidence (FTS5/BM25 retrieval)\n"]
        for i, ex in enumerate(examples[:max_examples], 1):
            doc = getattr(ex, "document_name", "unknown")
            heading = getattr(ex, "canonical_heading", "")
            text = getattr(ex, "text", "")
            score = getattr(ex, "score", 0.0)
            content_class = getattr(ex, "content_class", "")
            parts.append(
                f"\n### Evidence {i} [{doc}] (BM25 score: {score:.3f})\n"
                f"**Heading:** {heading}\n"
                f"**Content class:** {content_class}\n\n"
                f"{text[:max_chars]}\n"
            )
        return "".join(parts)

    def _assumption_register(self) -> dict[str, Any] | None:
        register = self._run.assumption_register
        if isinstance(register, dict):
            return register
        return None

    def _load_schema(self) -> dict[str, Any]:
        with open(self._schema_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _section_info(self, section_id: str, sub_section_id: str | None = None) -> dict[str, Any]:
        for sec in self._schema["sections"]:
            if sec["section_id"] != section_id:
                continue
            if sub_section_id is None:
                return sec
            for ss in sec.get("sub_sections", []):
                if ss["sub_section_id"] == sub_section_id:
                    return ss
        return {}

    def _section_guidance(self, section_id: str, sub_section_id: str | None = None) -> str:
        info = self._section_info(section_id, sub_section_id)
        return info.get("guidance", "")

    def _review_sensitivity(self, section_id: str, sub_section_id: str | None = None) -> str:
        info = self._section_info(section_id, sub_section_id)
        return info.get("review_sensitivity", "LOW")

    def _content_class(self, section_id: str, sub_section_id: str | None = None) -> str:
        info = self._section_info(section_id, sub_section_id)
        return info.get("content_class", "NARRATIVE")

    def _is_high_review(self, section_id: str, sub_section_id: str | None = None) -> bool:
        return self._review_sensitivity(section_id, sub_section_id) in ("HIGH", "CRITICAL")

    def _is_critical(self, section_id: str, sub_section_id: str | None = None) -> bool:
        return self._review_sensitivity(section_id, sub_section_id) == "CRITICAL"

    def _build_prompt(
        self,
        section_id: str,
        sub_section_id: str | None,
        examples: Sequence[Any],
        project_input: ProjectInput | None = None,
    ) -> str:
        info = self._section_info(section_id, sub_section_id)
        heading = info.get("heading", f"Section {section_id}")
        guidance = info.get("guidance", "")
        content_class = self._content_class(section_id, sub_section_id)
        review_sens = self._review_sensitivity(section_id, sub_section_id)
        fact_entries = relevant_fact_entries(
            self._assumption_register(), section_id, sub_section_id
        )
        synthetic = synthetic_entries(fact_entries)

        prompt_parts = [
            "# PDD Section Draft Request\n",
            f"## Section: {heading} ({section_id}"
            f"{'.' + sub_section_id if sub_section_id else ''})\n",
            f"Content class: {content_class}\n",
            f"Review sensitivity: {review_sens}\n",
            f"Guidance: {guidance}\n",
        ]

        if self._use_v2_prompt:
            prompt_parts.append(
                "\n## Authority Order\n"
                "Resolve conflicts: Input YAML > Evidence > VCS Template > "
                "Methodology > Examples > Domain Logic\n"
            )
            prompt_parts.append(
                "\n## Anti-Hallucination Markers\n"
                "- `[MISSING]` — required data not provided\n"
                "- `[INFERENCE]` — logically inferred, not directly stated\n"
                "- `[REVIEW REQUIRED]` — needs expert verification\n"
                "Cite evidence: `[E001]`, `[CORPUS: ...]`, `[METHODOLOGY: ...]`, "
                "`[CALC: ...]`, `[USER INPUT: ...]`\n"
            )
            overlay = self._load_overlay()
            if overlay:
                prompt_parts.append(f"\n{overlay}\n")

        if self._should_inject_retrieval():
            prompt_parts.append(
                self._format_retrieval_results(
                    examples, self._max_corpus_examples(), self._max_corpus_chars()
                )
            )
        elif examples:
            prompt_parts.append("\n## Corpus Examples (for structure only)\n")
            for i, ex in enumerate(examples[:3], 1):
                doc = getattr(ex, "document_name", "unknown")
                heading_ex = getattr(ex, "canonical_heading", "")
                text_ex = getattr(ex, "text", "")
                prompt_parts.append(
                    f"\n### Example {i} [{doc}]\n**Heading:** {heading_ex}\n\n{text_ex[:1000]}\n"
                )
        else:
            prompt_parts.append("\n## Corpus Examples: NONE — human review required.\n")

        if self._should_inject_calc() and self._is_quantification_section(
            section_id, sub_section_id
        ):
            prompt_parts.append(self._format_calc_injection())

        prompt_parts.append("\n## Project-Specific Facts\n")
        if project_input:
            prompt_parts.append(self._summarize_project())
        else:
            prompt_parts.append("ProjectInput not provided — all content must be placeholder.\n")

        if project_input and getattr(project_input, "evidence_registry", None):
            evidence_text = self._format_evidence_registry(project_input.evidence_registry)
            if evidence_text:
                prompt_parts.append(evidence_text)

        if fact_entries:
            prompt_parts.append("\n## Fact Provenance\n")
            for entry in fact_entries:
                marker = "REVIEW-GATED" if entry.get("blocked_review") else "OK"
                prompt_parts.append(
                    f"- {entry['field_path']}: {entry.get('value')} "
                    f"[{entry.get('source_type', 'unknown')}; confidence={entry.get('confidence', 'unknown')}; {marker}]\n"
                )
        if synthetic:
            prompt_parts.append("\n## Synthetic Assumptions In Scope\n")
            for entry in synthetic:
                prompt_parts.append(
                    f"- {entry['field_path']}: label as synthetic assumption; rationale={entry.get('rationale', '')}\n"
                )

        prompt_parts.append("\n## Instructions\n")
        if self._use_v2_prompt:
            prompt_parts.append(
                "1. Write only supported content — cite evidence using `[E001]`, `[CORPUS: ...]`, or `[CALC: ...]`.\n"
                "2. Do NOT invent numbers, statistics, or case studies not in the evidence.\n"
                "3. HIGH/CRITICAL sections require at least one cited corpus example.\n"
                "4. Mark unsupported claims: `[REVIEW REQUIRED: ...]`.\n"
                "5. Mark missing data: `[MISSING]`. Mark inferences: `[INFERENCE]`.\n"
                "6. If a synthetic assumption materially affects the section, label it explicitly.\n"
                "7. For quantitative sections, use `[CALC: component]` citations for calc engine values.\n"
                "8. Respect the authority order — never let domain logic override user input.\n"
                "9. Keep body text readable; move provenance details to a footer.\n"
                "10. Format output as Markdown.\n"
            )
        else:
            prompt_parts.append(
                "1. Write only supported content — cite CORPUS or METHODOLOGY sources.\n"
                "2. Do NOT invent numbers, statistics, or case studies not in the corpus.\n"
                "3. HIGH/CRITICAL sections require at least one cited corpus example.\n"
                "4. Unsupported claims must be marked [REVIEW REQUIRED: ...].\n"
                "5. If a synthetic assumption materially affects the section, label it explicitly in prose or a note.\n"
                "6. Keep body text readable and move detailed provenance burden to notes/appendices.\n"
                "7. Format output as Markdown.\n"
            )
        return "".join(prompt_parts)

    def _summarize_project(self) -> str:
        if not self._project:
            return "ProjectInput not available.\n"
        p = self._project
        if self._calc_is_authoritative() and self._calc_result is not None:
            net = self._calc_result.net_emission_reductions_tco2e
        else:
            net = p.quantification.net_emissions_tco2e_per_year
        net_str = f"{net:,.0f}" if net is not None else "TBD"
        parts = [
            f"- Project: {p.project.project_name}",
            f"- Location: {p.location.city}, {p.location.country}",
            f"- Methodology: {', '.join(p.technology.methodology_ids)}",
            f"- Technology: {p.technology.technology_type}",
            f"- Capacity: {p.technology.installed_capacity_mw} MW",
            f"- Annual waste: {p.technology.annual_waste_throughput:,.0f} tonnes/year",
            f"- Net tCO2e/yr: {net_str}",
            f"- Crediting period: {p.dates.crediting_period_years} years",
        ]
        return "\n".join(parts) + "\n"

    def _format_evidence_registry(self, registry: Any) -> str:
        """Format the evidence registry for injection into the drafting prompt."""
        if not registry or not getattr(registry, "items", None):
            return ""
        parts = ["\n## Evidence Registry (cite these IDs)\n"]
        for item in registry.items:
            eid = getattr(item, "evidence_id", "?")
            source_type = getattr(item, "source_type", "unknown")
            description = getattr(item, "description", "")
            section_ref = getattr(item, "section_ref", None)
            ref_str = f" (section {section_ref})" if section_ref else ""
            parts.append(f"- [{eid}] {source_type}: {description}{ref_str}\n")
        return "".join(parts)

    def draft_section(
        self,
        section_id: str,
        sub_section_id: str | None = None,
        examples: Sequence[Any] | None = None,
        force_regenerate: bool = False,
    ) -> DraftSection:
        """Draft a single section and store result in the run record."""
        key = f"{section_id}/{sub_section_id or ''}"
        if key in self._drafted and not force_regenerate:
            return self._drafted[key]

        logger.info("drafting_section", section_id=section_id, sub_section_id=sub_section_id)

        try:
            self._budget.check_budget()
        except BudgetExhaustedError as exc:
            logger.error("budget_exhausted", section_id=section_id, error=str(exc))
            return self._store_draft(
                key,
                DraftSection(
                    section_id=section_id,
                    sub_section_id=sub_section_id or "",
                    text=f"[BUDGET EXHAUSTED — {section_id}] Token budget exceeded. "
                    "Remaining sections require a new run or increased budget.",
                    confidence="UNSUPPORTED",
                    provenance=[],
                    issues=[f"BUDGET EXHAUSTED: {exc}"],
                    provider=getattr(self._provider, "name", "noop"),
                ),
            )

        sensitivity = self._review_sensitivity(section_id, sub_section_id)
        content_class = self._content_class(section_id, sub_section_id)

        k = self._max_corpus_examples()
        if examples is None:
            if self._should_inject_retrieval():
                heading = self._section_info(section_id, sub_section_id).get("heading", "")
                examples = get_examples_for_section(section_id, sub_section_id, k=k)
                if len(examples) < 2 and heading:
                    extras = get_section_heading_examples(heading, k=min(3, k))
                    seen = {
                        (getattr(e, "document_name", ""), getattr(e, "canonical_heading", ""))
                        for e in examples
                    }
                    for ex in extras:
                        if (
                            getattr(ex, "document_name", ""),
                            getattr(ex, "canonical_heading", ""),
                        ) not in seen:
                            examples.append(ex)
            else:
                examples = get_examples_for_section(section_id, sub_section_id, k=k)
        examples = list(examples)
        fact_entries = relevant_fact_entries(
            self._assumption_register(), section_id, sub_section_id
        )
        synthetic = synthetic_entries(fact_entries)

        prompt = self._build_prompt(section_id, sub_section_id, examples, self._project)

        provenance = [
            f"[CORPUS: {getattr(e, 'document_name', '?')}, {getattr(e, 'canonical_heading', '?')}]"
            for e in examples
        ]

        draft = self._provider.draft_section(
            section_id=section_id,
            sub_section_id=sub_section_id or "",
            prompt=prompt,
            provenance=provenance,
        )

        draft = self._enrich_draft(
            draft,
            section_id=section_id,
            sub_section_id=sub_section_id,
            sensitivity=sensitivity,
            content_class=content_class,
            fact_entries=fact_entries,
            synthetic=synthetic,
            provenance=provenance,
            examples=examples,
        )

        if self._enable_judge:
            draft = self._run_judge_redraft_loop(
                draft=draft,
                original_prompt=prompt,
                provenance=provenance,
                section_id=section_id,
                sub_section_id=sub_section_id,
                sensitivity=sensitivity,
                content_class=content_class,
                fact_entries=fact_entries,
                synthetic=synthetic,
            )

        if self._is_demo_run() and not self._enable_judge:
            draft.confidence = "HIGH"
            draft.issues = [
                issue for issue in draft.issues if not issue.startswith("REVIEW REQUIRED:")
            ]
            return self._store_draft(key, draft)

        return self._store_draft(key, draft)

    def _enrich_draft(
        self,
        draft: DraftSection,
        section_id: str,
        sub_section_id: str | None,
        sensitivity: str,
        content_class: str,
        fact_entries: list[dict[str, Any]],
        synthetic: list[dict[str, Any]],
        provenance: list[str],
        examples: Sequence[Any],
    ) -> DraftSection:
        """Attach schema metadata, provenance, and synthetic-guard checks to a draft."""
        draft.section_id = section_id
        draft.sub_section_id = sub_section_id or ""
        output_reference = {
            "type": output_ref_for_section(content_class),
            "description": "section draft content",
        }
        draft.fact_provenance = fact_entries
        draft.synthetic_uses = [dict(item, output_reference=output_reference) for item in synthetic]
        draft.output_references = [output_reference]
        draft.review_sensitivity = sensitivity
        draft.content_class = content_class
        draft.structured_content = self._build_structured_content(draft.sub_section_id)

        if sensitivity in ("HIGH", "CRITICAL") and not provenance:
            draft.issues.append(
                f"REVIEW REQUIRED: {section_id}"
                f"{'.' + sub_section_id if sub_section_id else ''} has HIGH/CRITICAL "
                f"review sensitivity but no corpus examples were retrieved."
            )
            draft.confidence = "LOW"

        if self._is_critical(section_id, sub_section_id) and not examples:
            draft.confidence = "UNSUPPORTED"
            draft.issues.append(
                f"CRITICAL section {section_id} has no corpus examples — "
                f"human expert sign-off required before this section is considered valid."
            )

        synthetic_source_types = list(
            dict.fromkeys(
                str(item.get("source_type"))
                for item in synthetic
                if item.get("source_type") is not None
            )
        )
        blocked_synthetic = [item for item in synthetic if item.get("blocked_review")]
        if synthetic:
            draft.issues.append(
                "ASSUMPTION DISCLOSURE: "
                f"{len(synthetic)} synthetic/demo-backed field(s) affect this section "
                f"({', '.join(synthetic_source_types)})."
            )
            if draft.confidence == "HIGH":
                draft.confidence = "MEDIUM"

        if blocked_synthetic and sensitivity in ("HIGH", "CRITICAL"):
            draft.confidence = "LOW" if sensitivity == "HIGH" else "UNSUPPORTED"
            paths = ", ".join(item["field_path"] for item in blocked_synthetic)
            draft.issues.append(
                f"REVIEW REQUIRED: {section_id}{'.' + sub_section_id if sub_section_id else ''} depends on review-gated synthetic inputs: {paths}"
            )
        elif synthetic and sensitivity in ("HIGH", "CRITICAL") and draft.confidence == "MEDIUM":
            draft.issues.append(
                f"REVIEW REQUIRED: {section_id}{'.' + sub_section_id if sub_section_id else ''} uses synthetic or demo defaults and must stay review-gated."
            )

        return draft

    def _resolve_judge_provider(self, drafting_provider_name: str) -> tuple[str, bool]:
        """Resolve (and cache) which provider judges this run's drafts, never itself.

        Cached per orchestrator instance so a 36-section run probes provider
        availability (which includes a live Ollama reachability check) once,
        not once per section.
        """
        if self._judge_provider_cache is None:
            self._judge_provider_cache = resolve_judge_provider(drafting_provider_name)
        return self._judge_provider_cache

    def _run_judge_redraft_loop(
        self,
        draft: DraftSection,
        original_prompt: str,
        provenance: list[str],
        section_id: str,
        sub_section_id: str | None,
        sensitivity: str,
        content_class: str,
        fact_entries: list[dict[str, Any]],
        synthetic: list[dict[str, Any]],
    ) -> DraftSection:
        """Judge a draft and auto-redraft up to max attempts if critical findings exist."""
        drafting_provider_name = getattr(self._provider, "name", "demo")
        judge_provider_name, judge_use_llm = self._resolve_judge_provider(drafting_provider_name)
        judge = LLMJudge(
            provider_name=judge_provider_name,
            use_llm=judge_use_llm,
            methodology_ids=(
                list(self._project.technology.methodology_ids)
                if self._project and self._project.technology.methodology_ids
                else None
            ),
            token_budget=self._budget,
        )
        section_key = f"{section_id}/{sub_section_id or ''}"
        current_draft = draft

        for attempt in range(1, self._max_redraft_attempts + 1):
            result = judge.judge_section(current_draft, self._project, self._calc_result)
            if result.passed:
                self._run.notes.append(
                    f"judge: {section_key} passed on attempt {attempt} "
                    f"(score={result.score}, provider={judge.provider_name})"
                )
                return current_draft

            critical = result.categories.get("critical", [])
            if not critical:
                self._run.notes.append(
                    f"judge: {section_key} has advisory findings only on attempt {attempt} "
                    f"(score={result.score})"
                )
                return current_draft

            if attempt == self._max_redraft_attempts:
                current_draft.confidence = "UNSUPPORTED"
                current_draft.issues.append(
                    f"JUDGE REDRAFT FAILED after {self._max_redraft_attempts} attempts: "
                    f"{'; '.join(critical)}"
                )
                self._run.notes.append(
                    f"judge: {section_key} failed after {self._max_redraft_attempts} attempts; "
                    f"parked for domain review (tokens_used={self._budget.total_tokens}, "
                    f"estimated_cost_usd={round(self._budget.estimated_cost_usd, 4)})"
                )
                self._park_section_for_domain_review(section_id, sub_section_id or "", critical)
                return current_draft

            redraft_prompt = self._build_redraft_prompt(original_prompt, result)
            logger.info(
                "judge_redraft_attempt",
                section_key=section_key,
                attempt=attempt,
                critical_count=len(critical),
            )
            self.redraft_count += 1
            current_draft = self._provider.draft_section(
                section_id=section_id,
                sub_section_id=sub_section_id or "",
                prompt=redraft_prompt,
                provenance=provenance + [f"[JUDGE: redraft attempt {attempt}]"],
            )
            current_draft = self._enrich_draft(
                current_draft,
                section_id=section_id,
                sub_section_id=sub_section_id,
                sensitivity=sensitivity,
                content_class=content_class,
                fact_entries=fact_entries,
                synthetic=synthetic,
                provenance=provenance + [f"[JUDGE: redraft attempt {attempt}]"],
                examples=[],
            )

        return current_draft

    def _build_redraft_prompt(self, original_prompt: str, judge_result: Any) -> str:
        """Append judge feedback to the original prompt for a redraft."""
        feedback_lines: list[str] = []
        for category in ("critical", "advisory"):
            for message in judge_result.categories.get(category, []):
                feedback_lines.append(f"- [{category.upper()}] {message}")
        feedback = "\n".join(feedback_lines)
        return (
            f"{original_prompt}\n\n"
            "## Prior Judge Feedback — address every CRITICAL item before redrafting\n"
            f"{feedback}\n\n"
            "Revise the section to resolve all critical findings. Keep the same section scope, "
            "preserve required evidence citations, and maintain the anti-hallucination marker style."
        )

    def _park_section_for_domain_review(
        self,
        section_id: str,
        sub_section_id: str,
        reasons: list[str],
    ) -> None:
        """Log a section state transition to needs-domain-review after judge failure."""
        try:
            project_name = self._project.project.project_name if self._project else "unknown"
            store = init_review_state(
                run_id=self._run_id,
                project_name=project_name,
                section_ids=[(section_id, sub_section_id)],
            )
            store.set_state(
                section_id=section_id,
                sub_section_id=sub_section_id,
                new_state=ReviewState.NEEDS_DOMAIN_REVIEW,
                reviewer_notes="Judge critical findings: " + "; ".join(reasons),
                updated_by="judge",
            )
            store.save(output_dir=self._runs_dir)
            logger.info(
                "judge_parked_section",
                run_id=self._run_id,
                section_id=section_id,
                sub_section_id=sub_section_id,
            )
        except Exception as exc:
            logger.warning(
                "judge_park_section_failed",
                run_id=self._run_id,
                section_id=section_id,
                sub_section_id=sub_section_id,
                error=str(exc),
            )

    def redraft_section(self, section_id: str, sub_section_id: str | None = None) -> DraftSection:
        """Manually trigger a judge-enabled redraft of an existing section."""
        previous = self._enable_judge
        self._enable_judge = True
        try:
            return self.draft_section(section_id, sub_section_id, force_regenerate=True)
        finally:
            self._enable_judge = previous

    def _store_draft(self, key: str, draft: DraftSection) -> DraftSection:
        self._drafted[key] = draft
        self._run.add(draft)
        return draft

    def draft_all_sections(self) -> list[DraftSection]:
        """Draft all sections in the canonical schema order."""
        results: list[DraftSection] = []
        for sec in self._schema["sections"]:
            sid = sec["section_id"]
            for ss in sec.get("sub_sections", []):
                ssid = ss["sub_section_id"]
                draft = self.draft_section(sid, ssid)
                results.append(draft)
        return results

    def draft_project_details(self) -> list[DraftSection]:
        """Draft all sub-sections of Section 1 (Project Details)."""
        sid = "1"
        results: list[DraftSection] = []
        for ss in self._schema["sections"][0].get("sub_sections", []):
            ssid = ss["sub_section_id"]
            results.append(self.draft_section(sid, ssid))
        return results

    def run(self) -> DraftRun:
        """Run the full drafting pipeline. Returns the DraftRun record."""
        logger.info(
            "orchestrator_run_start",
            run_id=self._run_id,
            project=self._project.project.project_name if self._project else "unknown",
            budget_max=self._budget.max_tokens,
            budget_max_cost_usd=self._budget.max_cost_usd,
            use_v2_prompt=self._use_v2_prompt,
            calc_injected=self._should_inject_calc(),
        )
        self.draft_all_sections()
        self._run.notes.append(f"token_budget: {self._budget.summary()}")
        logger.info(
            "orchestrator_run_complete",
            run_id=self._run_id,
            sections=len(self._run.sections),
            tokens_used=self._budget.total_tokens,
            budget_utilization=f"{self._budget.utilization:.1%}",
            estimated_cost_usd=round(self._budget.estimated_cost_usd, 4),
        )
        return self._run

    def run_review(self) -> dict[str, Any]:
        """Run all review and consistency checks against the drafted sections.

        Returns a dict with review_check_result and consistency_report summaries.
        Automatically persists the DraftRun if not already saved.
        """
        logger.info("review_run_start", run_id=self._run_id)

        self._run.save(output_dir=self._runs_dir)

        review_result = run_review_checks(
            draft_run=self._run,
            project_input=self._project,
            run_id=self._run_id,
        )

        section_ids = [(s.section_id, s.sub_section_id) for s in self._run.sections]
        state_store = init_review_state(
            run_id=self._run_id,
            project_name=self._project.project.project_name if self._project else "unknown",
            section_ids=section_ids,
        )

        for sid, ssid in section_ids:
            key = f"{sid}/{ssid}"
            draft = next(
                (s for s in self._run.sections if s.section_id == sid and s.sub_section_id == ssid),
                None,
            )
            if draft:
                blocked_synthetic = [
                    item for item in draft.synthetic_uses if item.get("blocked_review")
                ]
                if blocked_synthetic:
                    state_store.sections[key].state = ReviewState.NEEDS_DOMAIN_REVIEW
                    state_store.sections[key].reviewer_notes.append(
                        "Synthetic review gate: "
                        + ", ".join(item.get("field_path", "unknown") for item in blocked_synthetic)
                    )
                elif draft.confidence in ("HIGH",):
                    state_store.sections[key].state = ReviewState.READY_FOR_HUMAN_EDIT
                else:
                    state_store.sections[key].state = ReviewState.NEEDS_DOMAIN_REVIEW
                if draft.synthetic_uses and not blocked_synthetic:
                    state_store.sections[key].reviewer_notes.append(
                        f"Assumption burden: {len(draft.synthetic_uses)} synthetic/demo-backed input(s)."
                    )

                if self._is_demo_run():
                    state_store.sections[key].state = ReviewState.READY_FOR_HUMAN_EDIT
                    state_store.sections[key].reviewer_notes = [
                        note
                        for note in state_store.sections[key].reviewer_notes
                        if not note.startswith("Synthetic review gate:")
                    ]

        state_store.save(output_dir=self._runs_dir)

        consistency_report = check_quantitative_consistency(
            draft_sections=self._run.sections,
            project_input=self._project,
            run_id=self._run_id,
            calc_result=self._calc_result,
        )

        tbd_tracker = TBDTracker()
        tbd_report = tbd_tracker.scan(
            draft_sections=self._run.sections,
            run_id=self._run_id,
        )

        logger.info(
            "review_run_complete",
            run_id=self._run_id,
            review_passed=review_result.passed,
            consistency_passed=consistency_report.passed,
            tbd_count=tbd_report.count,
            blocking_issues=len(review_result.blocking_issues),
        )

        assumption_burden_path = write_assumption_burden_report(
            self._run.to_dict(), output_path=self._assumption_burden_path
        )

        return {
            "run_id": self._run_id,
            "review": summarize_review_result(review_result),
            "consistency": summarize_consistency_report(consistency_report),
            "tbd": tbd_report.to_dict(),
            "review_state_path": str(state_store.save(output_dir=self._runs_dir)),
            "draft_run_path": str(self._run.save(output_dir=self._runs_dir)),
            "assumption_burden_path": str(assumption_burden_path),
        }

    def attach_assumption_register(self, assumption_register: dict[str, Any] | None) -> None:
        """Attach a loaded assumption register to the run for section-level provenance routing."""
        if assumption_register is None:
            return
        self._run.assumption_register = assumption_register

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def draft_run(self) -> DraftRun:
        return self._run

    @property
    def drafted_sections(self) -> dict[str, DraftSection]:
        return dict(self._drafted)

    @property
    def token_budget(self) -> TokenBudget:
        return self._budget

    @property
    def calc_result(self) -> Any | None:
        return self._calc_result

    def set_calc_result(self, calc_result: Any) -> None:
        """Attach calc results for injection into quantification section prompts."""
        self._calc_result = calc_result
        if hasattr(calc_result, "to_dict"):
            self._run.calc_result = calc_result.to_dict()
