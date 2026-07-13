"""Provider that adapts full paragraphs from the indexed PDD corpus."""

from __future__ import annotations

import re
from collections.abc import Callable

from pdd_agent.drafting.fact_substitution import FactSubstitutionEngine
from pdd_agent.llm.provider import BaseProvider, DemoProvider, DraftSection
from pdd_agent.retrieval.search import RetrievalResult, get_examples_for_section
from schemas.project_input import ProjectInput


class CorpusProvider(BaseProvider):
    name = "corpus"

    def __init__(
        self,
        project_input: ProjectInput | None = None,
        *,
        retrieval: Callable[..., list[RetrievalResult]] = get_examples_for_section,
        fallback: BaseProvider | None = None,
    ) -> None:
        self._project_input = project_input
        self._retrieval = retrieval
        self._fallback = fallback or DemoProvider()

    def set_project_input(self, project_input: ProjectInput | None) -> None:
        self._project_input = project_input

    def draft_section(
        self,
        section_id: str,
        sub_section_id: str,
        prompt: str,
        provenance: list[str],
        max_chars: int = 4000,
    ) -> DraftSection:
        examples = self._retrieval(section_id, sub_section_id or None, k=3)
        eligible = [example for example in examples if len(example.text.strip()) >= 100]
        if not eligible:
            return self._fallback_section(section_id, sub_section_id, prompt, provenance, max_chars)

        source = max(eligible, key=lambda example: len(example.text.strip()))
        if source.content_class == "FACTUAL":
            return self._fallback_section(section_id, sub_section_id, prompt, provenance, max_chars)
        if source.content_class in {
            "METHODOLOGY_DEPENDENT",
            "QUANTITATIVE",
        } and not self._methodology_matches(source.text):
            return self._fallback_section(section_id, sub_section_id, prompt, provenance, max_chars)

        result = FactSubstitutionEngine(self._project_input).adapt(
            source.text,
            source_name=source.document_name,
        )
        source_marker = f"[CORPUS: {source.document_name}, {source.canonical_heading}]"
        issues = list(result.review_flags)
        return DraftSection(
            section_id=section_id,
            sub_section_id=sub_section_id,
            text=result.text[:max_chars],
            confidence="MEDIUM" if issues else "HIGH",
            provenance=[*provenance, source_marker],
            issues=issues,
            provider=self.name,
            fact_provenance=result.substitutions,
            content_class=source.content_class or "NARRATIVE",
            output_references=[{"type": "corpus_adaptation", "description": source.document_name}],
        )

    def _methodology_matches(self, text: str) -> bool:
        if self._project_input is None:
            return False
        source_ids = set(re.findall(r"\b(?:ACM|AM|VM)\d{4}\b", text.upper()))
        target_ids = {item.upper() for item in self._project_input.technology.methodology_ids}
        return not source_ids or bool(source_ids & target_ids)

    def _fallback_section(self, section_id, sub_section_id, prompt, provenance, max_chars):
        draft = self._fallback.draft_section(
            section_id, sub_section_id, prompt, provenance, max_chars
        )
        draft.text = f"[SYNTHETIC FALLBACK: corpus unavailable]\n{draft.text}"[:max_chars]
        draft.provider = self.name
        draft.issues.append("REVIEW REQUIRED: corpus adaptation fallback used")
        return draft

    def close(self) -> None:
        self._fallback.close()
