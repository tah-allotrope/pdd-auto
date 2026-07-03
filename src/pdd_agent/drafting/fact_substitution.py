"""Deterministic, auditable substitution of project facts in corpus prose."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from schemas.project_input import ProjectInput


@dataclass(frozen=True)
class SubstitutionResult:
    text: str
    substitutions: list[dict[str, str]] = field(default_factory=list)
    review_flags: list[str] = field(default_factory=list)


class FactSubstitutionEngine:
    """Replace explicitly identified source facts with ProjectInput values."""

    def __init__(self, project_input: ProjectInput | None = None) -> None:
        self.project_input = project_input

    def adapt(
        self,
        text: str,
        *,
        source_name: str,
        source_facts: dict[str, Any] | None = None,
    ) -> SubstitutionResult:
        source_facts = source_facts or {}
        replacements = self._replacement_values(source_facts)
        adapted = text
        changes: list[dict[str, str]] = []
        for field_name, old, new in replacements:
            if not old or old == new:
                continue
            pattern = re.compile(re.escape(old), re.IGNORECASE)
            adapted, count = pattern.subn(lambda _match, value=new: value, adapted)
            if count:
                changes.append({"field": field_name, "from": old, "to": new})

        flags: list[str] = []
        if re.search(r"\b(?:permit|regulation|decree|license|approval)\b", adapted, re.I):
            flags.append("[REVIEW: substitution ambiguity - regulatory reference retained]")
        marker = f"[ADAPTED FROM CORPUS: {source_name}]"
        output = f"{marker}\n{adapted.strip()}"
        if flags:
            output += "\n" + "\n".join(flags)
        return SubstitutionResult(output, changes, flags)

    def _replacement_values(self, source: dict[str, Any]) -> list[tuple[str, str, str]]:
        if self.project_input is None:
            return []
        project = self.project_input
        targets: dict[str, Any] = {
            "project_name": project.project.project_name,
            "proponent_name": project.project.proponent_name,
            "city": project.location.city,
            "region": project.location.region,
            "country": project.location.country,
            "installed_capacity_mw": project.technology.installed_capacity_mw,
            "annual_waste_throughput": project.technology.annual_waste_throughput,
            "methodology_ids": ", ".join(project.technology.methodology_ids),
            "start_date": project.dates.start_date,
            "crediting_period_start": project.dates.crediting_period_start,
        }
        replacements: list[tuple[str, str, str]] = []
        for key, new_value in targets.items():
            old_value = source.get(key)
            if old_value is not None and new_value is not None:
                replacements.append((key, str(old_value), str(new_value)))
        return replacements


def substitute_facts(
    text: str,
    project_input: ProjectInput,
    *,
    source_name: str,
    source_facts: dict[str, Any] | None = None,
) -> SubstitutionResult:
    return FactSubstitutionEngine(project_input).adapt(
        text, source_name=source_name, source_facts=source_facts,
    )
