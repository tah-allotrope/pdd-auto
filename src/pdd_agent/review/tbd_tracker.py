"""TBD / placeholder tracking for drafted sections.

Scans section text for TBD, PLACEHOLDER, INSERT, SOURCE, and EVIDENCE markers
and produces a structured report mapping each finding to its section and
suggesting the evidence type required from the section schema.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import yaml


_TBD_RE = re.compile(
    r"\[(TBD|PLACEHOLDER|INSERT|SOURCE|EVIDENCE)[^\]]*\]",
    re.IGNORECASE,
)


@dataclass
class TBDItem:
    section_id: str
    sub_section_id: str
    marker: str
    context: str
    line_number: int
    evidence_type: str | None = None


@dataclass
class TBDReport:
    run_id: str
    items: list[TBDItem] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.items)

    @property
    def sections_with_tbd(self) -> list[str]:
        keys: set[str] = set()
        for item in self.items:
            if not item.sub_section_id:
                key = item.section_id
            elif item.sub_section_id.startswith(item.section_id + "."):
                key = item.sub_section_id
            else:
                key = f"{item.section_id}.{item.sub_section_id}"
            keys.add(key)
        return sorted(keys)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "count": self.count,
            "sections_with_tbd": self.sections_with_tbd,
            "items": [
                {
                    "section_id": item.section_id,
                    "sub_section_id": item.sub_section_id,
                    "marker": item.marker,
                    "context": item.context,
                    "line_number": item.line_number,
                    "evidence_type": item.evidence_type,
                }
                for item in self.items
            ],
        }


def _load_schema(schema_path: Path | None = None) -> dict[str, Any]:
    path = schema_path or Path(__file__).parent.parent.parent.parent / "schemas" / "pdd_section_schema.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _evidence_for_section(schema: dict[str, Any], section_id: str, sub_section_id: str) -> str | None:
    for sec in schema.get("sections", []):
        if sec["section_id"] != section_id:
            continue
        for ss in sec.get("sub_sections", []):
            if ss.get("sub_section_id") == sub_section_id:
                evidence = ss.get("evidence_required")
                if evidence:
                    return "; ".join(evidence)
                return None
    return None


class TBDTracker:
    """Scan drafted sections for TBD/placeholder markers."""

    def __init__(self, schema_path: Path | None = None) -> None:
        self._schema = _load_schema(schema_path)

    def scan(
        self,
        draft_sections: Sequence[Any],
        run_id: str,
    ) -> TBDReport:
        """Scan sections and return a TBD report."""
        report = TBDReport(run_id=run_id)
        for section in draft_sections:
            sid = getattr(section, "section_id", "")
            ssid = getattr(section, "sub_section_id", "")
            text = getattr(section, "text", "") or ""
            lines = text.splitlines()
            for line_idx, line in enumerate(lines, start=1):
                for match in _TBD_RE.finditer(line):
                    marker = match.group(0)
                    context = line.strip()
                    evidence = _evidence_for_section(self._schema, sid, ssid)
                    report.items.append(
                        TBDItem(
                            section_id=sid,
                            sub_section_id=ssid,
                            marker=marker,
                            context=context,
                            line_number=line_idx,
                            evidence_type=evidence,
                        )
                    )
        return report
