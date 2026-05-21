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
from pdd_agent.llm.provider import (
    BaseProvider,
    DemoProvider,
    DraftRun,
    DraftSection,
    NoopProvider,
    get_provider_registry,
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
    search as retrieval_search,
)
from pdd_agent.review.checks import run_review_checks, summarize_review_result
from pdd_agent.review.consistency import (
    check_quantitative_consistency,
    summarize_consistency_report,
)
from pdd_agent.review.states import ReviewStateStore, init_review_state, ReviewState
from pdd_agent.review.tbd_tracker import TBDTracker
from schemas.project_input import ProjectInput

logger = structlog.get_logger()

_PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "prompts"
_SCHEMA_PATH = Path(__file__).parent.parent.parent.parent / "schemas" / "pdd_section_schema.yaml"


class SectionOrchestrator:
    """Orchestrates section-level retrieval, prompt assembly, and drafting."""

    def __init__(
        self,
        provider: BaseProvider | None = None,
        project_input: ProjectInput | None = None,
        run_id: str | None = None,
        schema_path: Path | None = None,
        prompts_dir: Path | None = None,
    ) -> None:
        self._provider = provider or NoopProvider()
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

    def _is_demo_run(self) -> bool:
        return getattr(self._provider, "name", "") == "demo"

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
            f"# PDD Section Draft Request\n",
            f"## Section: {heading} ({section_id}"
            f"{'.' + sub_section_id if sub_section_id else ''})\n",
            f"Content class: {content_class}\n",
            f"Review sensitivity: {review_sens}\n",
            f"Guidance: {guidance}\n",
        ]

        if examples:
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

        prompt_parts.append("\n## Project-Specific Facts\n")
        if project_input:
            prompt_parts.append(self._summarize_project())
        else:
            prompt_parts.append("ProjectInput not provided — all content must be placeholder.\n")

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
        parts = [
            f"- Project: {p.project.project_name}",
            f"- Location: {p.location.city}, {p.location.country}",
            f"- Methodology: {', '.join(p.technology.methodology_ids)}",
            f"- Technology: {p.technology.technology_type}",
            f"- Capacity: {p.technology.installed_capacity_mw} MW",
            f"- Annual waste: {p.technology.annual_waste_throughput:,.0f} tonnes/year",
            f"- Net tCO2e/yr: {p.quantification.net_emissions_tco2e_per_year:,.0f}",
            f"- Crediting period: {p.dates.crediting_period_years} years",
        ]
        return "\n".join(parts) + "\n"

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

        sensitivity = self._review_sensitivity(section_id, sub_section_id)
        content_class = self._content_class(section_id, sub_section_id)

        if examples is None:
            examples = get_examples_for_section(section_id, sub_section_id, k=5)
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

        if self._is_demo_run():
            draft.confidence = "HIGH"
            draft.issues = [
                issue for issue in draft.issues if not issue.startswith("REVIEW REQUIRED:")
            ]
            return self._store_draft(key, draft)

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

        return self._store_draft(key, draft)

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
        )
        self.draft_all_sections()
        logger.info(
            "orchestrator_run_complete", run_id=self._run_id, sections=len(self._run.sections)
        )
        return self._run

    def run_review(self) -> dict[str, Any]:
        """Run all review and consistency checks against the drafted sections.

        Returns a dict with review_check_result and consistency_report summaries.
        Automatically persists the DraftRun if not already saved.
        """
        logger.info("review_run_start", run_id=self._run_id)

        self._run.save()

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

        state_store.save()

        consistency_report = check_quantitative_consistency(
            draft_sections=self._run.sections,
            project_input=self._project,
            run_id=self._run_id,
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

        assumption_burden_path = write_assumption_burden_report(self._run.to_dict())

        return {
            "run_id": self._run_id,
            "review": summarize_review_result(review_result),
            "consistency": summarize_consistency_report(consistency_report),
            "tbd": tbd_report.to_dict(),
            "review_state_path": str(state_store.save()),
            "draft_run_path": str(self._run.save()),
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
