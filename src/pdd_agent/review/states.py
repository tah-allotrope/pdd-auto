"""Review/approval state model with JSON persistence.

Provides a state machine for section-level approval workflow:
  drafted → needs-input → drafted
  drafted → needs-domain-review → ready-for-human-edit
  drafted → needs-domain-review → drafted
  drafted → ready-for-human-edit → approved
  drafted → approved
  needs-input → drafted
  ready-for-human-edit → needs-domain-review
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

import structlog

logger = structlog.get_logger()

_VALID_STATES = {
    "drafted",
    "needs-input",
    "needs-domain-review",
    "ready-for-human-edit",
    "approved",
}

_TRANSITIONS: dict[str, set[str]] = {
    "drafted": {"needs-input", "needs-domain-review", "ready-for-human-edit"},
    "needs-input": {"drafted"},
    "needs-domain-review": {"ready-for-human-edit", "drafted"},
    "ready-for-human-edit": {"approved", "needs-domain-review"},
    "approved": set(),
}


class ReviewState(str, Enum):
    DRAFTED = "drafted"
    NEEDS_INPUT = "needs-input"
    NEEDS_DOMAIN_REVIEW = "needs-domain-review"
    READY_FOR_HUMAN_EDIT = "ready-for-human-edit"
    APPROVED = "approved"

    def can_transition_to(self, target: "ReviewState") -> bool:
        return target.value in _TRANSITIONS.get(self.value, set())

    def label(self) -> str:
        return {
            "drafted": "Drafted (auto)",
            "needs-input": "Needs Input",
            "needs-domain-review": "Needs Domain Review",
            "ready-for-human-edit": "Ready for Human Edit",
            "approved": "Approved",
        }.get(self.value, self.value)


@dataclass
class SectionState:
    section_id: str
    sub_section_id: str
    state: ReviewState = ReviewState.DRAFTED
    reviewer_notes: list[str] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_by: str = "system"

    def key(self) -> str:
        return f"{self.section_id}/{self.sub_section_id}"

    def to_dict(self) -> dict:
        return {
            "section_id": self.section_id,
            "sub_section_id": self.sub_section_id,
            "state": self.state.value,
            "reviewer_notes": self.reviewer_notes,
            "last_updated": self.last_updated,
            "updated_by": self.updated_by,
        }


@dataclass
class ReviewStateStore:
    run_id: str
    project_name: str
    sections: dict[str, SectionState] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def get_or_create(self, section_id: str, sub_section_id: str) -> SectionState:
        key = f"{section_id}/{sub_section_id}"
        if key not in self.sections:
            self.sections[key] = SectionState(
                section_id=section_id,
                sub_section_id=sub_section_id,
            )
        return self.sections[key]

    def set_state(
        self,
        section_id: str,
        sub_section_id: str,
        new_state: ReviewState,
        reviewer_notes: str | None = None,
        updated_by: str = "human",
    ) -> tuple[bool, str]:
        state_obj = self.get_or_create(section_id, sub_section_id)
        if not state_obj.state.can_transition_to(new_state):
            return (
                False,
                f"Invalid transition: {state_obj.state.label()} → {new_state.label()}. "
                f"Allowed: {[s.label() for s in ReviewState if state_obj.state.can_transition_to(s)]}",
            )
        state_obj.state = new_state
        state_obj.last_updated = datetime.now().isoformat()
        state_obj.updated_by = updated_by
        if reviewer_notes:
            state_obj.reviewer_notes.append(reviewer_notes)
        self.updated_at = datetime.now().isoformat()
        return True, "ok"

    def add_note(
        self, section_id: str, sub_section_id: str, note: str, updated_by: str = "human"
    ) -> None:
        state_obj = self.get_or_create(section_id, sub_section_id)
        state_obj.reviewer_notes.append(note)
        state_obj.last_updated = datetime.now().isoformat()
        state_obj.updated_by = updated_by
        self.updated_at = datetime.now().isoformat()

    def is_all_approved(self) -> bool:
        return all(s.state == ReviewState.APPROVED for s in self.sections.values())

    def blocking_states(self) -> list[str]:
        return [
            f"{s.section_id}.{s.sub_section_id}: {s.state.label()}"
            for s in self.sections.values()
            if s.state in (ReviewState.NEEDS_INPUT, ReviewState.NEEDS_DOMAIN_REVIEW)
        ]

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "project_name": self.project_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "sections": {k: s.to_dict() for k, s in self.sections.items()},
            "all_approved": self.is_all_approved(),
            "blocking_states": self.blocking_states(),
        }

    def save(self, output_dir: Path | None = None) -> Path:
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent.parent / "data" / "runs"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"review-state-{self.run_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info("review_state_saved", run_id=self.run_id, path=str(path))
        return path

    @classmethod
    def load(cls, run_id: str, output_dir: Path | None = None) -> "ReviewStateStore":
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent.parent / "data" / "runs"
        output_dir = Path(output_dir)
        path = output_dir / f"review-state-{run_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"No review state found for run_id: {run_id}")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        store = cls(run_id=data["run_id"], project_name=data["project_name"])
        for key, sec_data in data.get("sections", {}).items():
            state = SectionState(
                section_id=sec_data["section_id"],
                sub_section_id=sec_data["sub_section_id"],
                state=ReviewState(sec_data["state"]),
                reviewer_notes=sec_data.get("reviewer_notes", []),
                last_updated=sec_data.get("last_updated", ""),
                updated_by=sec_data.get("updated_by", "unknown"),
            )
            store.sections[key] = state
        return store


def init_review_state(
    run_id: str, project_name: str, section_ids: list[tuple[str, str]]
) -> ReviewStateStore:
    store = ReviewStateStore(run_id=run_id, project_name=project_name)
    for sid, ssid in section_ids:
        store.get_or_create(sid, ssid)
    return store
