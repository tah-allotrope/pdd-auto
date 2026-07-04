"""Methodology screening: match project descriptions against active methodologies.

Loads Verra VCS and CDM methodology databases, scores applicability against
project descriptions or extracted ProjectInput, and returns ranked suggestions
with confidence scores.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog
import yaml

from schemas.project_input import ProjectInput, SuggestedMethodology
from pdd_agent.llm.provider import BaseProvider

logger = structlog.get_logger()

_DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "methodologies"
_VCS_PATH = _DATA_DIR / "verra_vcs_active.json"
_CDM_PATH = _DATA_DIR / "cdm_active.json"
_RULES_DIR = Path(__file__).parent.parent.parent.parent / "rules" / "verra"


class ScreeningError(Exception):
    """Raised when methodology screening fails."""


class MethodologyDatabase:
    """Loads and queries methodology data files and per-family rule files."""

    def __init__(
        self,
        vcs_path: Path | None = None,
        cdm_path: Path | None = None,
        rules_dir: Path | None = None,
    ) -> None:
        self._vcs_path = vcs_path or _VCS_PATH
        self._cdm_path = cdm_path or _CDM_PATH
        self._rules_dir = rules_dir or _RULES_DIR
        self._vcs: list[dict[str, Any]] = []
        self._cdm: list[dict[str, Any]] = []
        self._rules_by_id: dict[str, dict[str, Any]] = {}
        self._all: list[dict[str, Any]] = []
        self._load()

    def _load_rules(self) -> None:
        if not self._rules_dir.exists():
            logger.warning("rules_dir_not_found", path=str(self._rules_dir))
            return
        for path in sorted(self._rules_dir.glob("*_rules.yaml")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                for mid, mdata in (data.get("methodologies") or {}).items():
                    self._rules_by_id[mid] = {
                        **mdata,
                        "_rules_file": path.name,
                        "_rules_version": data.get("version", "unknown"),
                    }
                logger.info("methodology_rules_loaded", file=path.name, count=len(data.get("methodologies") or {}))
            except Exception as exc:  # noqa: BLE001
                logger.warning("methodology_rules_load_failed", file=path.name, error=str(exc))

    def _load(self) -> None:
        self._load_rules()

        if self._vcs_path.exists():
            with open(self._vcs_path, encoding="utf-8") as f:
                data = json.load(f)
            self._vcs = data.get("methodologies", [])
            logger.info("vcs_methodologies_loaded", count=len(self._vcs))
        else:
            logger.warning("vcs_data_not_found", path=str(self._vcs_path))

        if self._cdm_path.exists():
            with open(self._cdm_path, encoding="utf-8") as f:
                data = json.load(f)
            self._cdm = data.get("methodologies", [])
            logger.info("cdm_methodologies_loaded", count=len(self._cdm))
        else:
            logger.warning("cdm_data_not_found", path=str(self._cdm_path))

        # Build a unified, de-duplicated methodology list enriched with rules.
        seen_ids: set[str] = set()
        unified: list[dict[str, Any]] = []
        for m in self._vcs + self._cdm:
            mid = m["id"]
            if mid in seen_ids:
                continue
            seen_ids.add(mid)
            enriched = dict(m)
            rules = self._rules_by_id.get(mid)
            if rules:
                enriched.update(rules)
            unified.append(enriched)

        # Add methodologies that exist only in rules (new families).
        for mid, rules in self._rules_by_id.items():
            if mid in seen_ids:
                continue
            seen_ids.add(mid)
            unified.append({
                "id": mid,
                "name": rules.get("full_name", mid),
                "version": rules.get("version"),
                "category": rules.get("category", "other"),
                **rules,
            })

        self._all = unified

    @property
    def all_methodologies(self) -> list[dict[str, Any]]:
        return list(self._all)

    @property
    def data_version(self) -> str:
        vcs_meta = {}
        cdm_meta = {}
        if self._vcs_path.exists():
            with open(self._vcs_path, encoding="utf-8") as f:
                vcs_meta = json.load(f).get("_meta", {})
        if self._cdm_path.exists():
            with open(self._cdm_path, encoding="utf-8") as f:
                cdm_meta = json.load(f).get("_meta", {})
        vcs_date = vcs_meta.get("last_updated", "unknown")
        cdm_date = cdm_meta.get("last_updated", "unknown")
        rules_date = ",".join(
            sorted({r.get("_rules_version", "unknown") for r in self._rules_by_id.values()})
        ) or "no_rules"
        return f"VCS:{vcs_date}, CDM:{cdm_date}, RULES:{rules_date}"


def _score_technology_match(
    methodology: dict[str, Any],
    technology_type: str | None,
) -> float:
    """Score how well the project's technology matches the methodology."""
    applicable = methodology.get("applicable_technology_types", [])
    if not applicable:
        return 0.0
    if technology_type and technology_type in applicable:
        return 1.0
    return 0.0


def _score_waste_match(
    methodology: dict[str, Any],
    waste_types: list[str] | None,
) -> float:
    """Score how well the project's waste types match the methodology."""
    meth_wastes = methodology.get("waste_types", [])
    if not meth_wastes or not waste_types:
        return 0.0

    matches = sum(1 for w in waste_types if w in meth_wastes)
    return matches / len(waste_types) if waste_types else 0.0


def _score_category_match(
    methodology: dict[str, Any],
    description_lower: str,
) -> float:
    """Score category relevance based on description keywords."""
    category = methodology.get("category", "")
    category_keywords: dict[str, list[str]] = {
        "waste": ["waste", "landfill", "disposal", "swds", "organic", "composting", "anaerobic"],
        "waste_handling_and_disposal": ["waste", "landfill", "disposal", "swds", "organic"],
        "energy_industries": ["energy", "power", "electricity", "fuel", "cement", "biomass"],
        "afolu": ["forest", "deforestation", "redd", "agriculture", "land use"],
    }
    keywords = category_keywords.get(category, [])
    if not keywords:
        return 0.0
    matches = sum(1 for kw in keywords if kw in description_lower)
    return min(matches / max(len(keywords) * 0.5, 1), 1.0)


def _score_applicability_conditions(
    methodology: dict[str, Any],
    description_lower: str,
) -> float:
    """Score how many applicability conditions are mentioned in the description."""
    conditions = methodology.get("applicability_conditions", [])
    if not conditions:
        return 0.5

    matches = 0
    for condition in conditions:
        condition_text = condition["text"] if isinstance(condition, dict) else condition
        condition_words = set(condition_text.lower().split())
        key_words = {w for w in condition_words if len(w) > 4}
        if not key_words:
            continue
        word_matches = sum(1 for w in key_words if w in description_lower)
        if word_matches >= len(key_words) * 0.3:
            matches += 1

    return matches / len(conditions) if conditions else 0.0


def _score_methodology_id_mentioned(
    methodology: dict[str, Any],
    description_lower: str,
) -> float:
    """Check if the methodology ID is directly mentioned in the description."""
    mid = methodology["id"].lower()
    if mid in description_lower:
        return 1.0
    name_words = methodology.get("name", "").lower().split()
    key_name_words = [w for w in name_words if len(w) > 5]
    if key_name_words:
        matches = sum(1 for w in key_name_words if w in description_lower)
        if matches >= len(key_name_words) * 0.6:
            return 0.3
    return 0.0


def screen_methodologies(
    project_description: str,
    project_input: ProjectInput | None = None,
    *,
    db: MethodologyDatabase | None = None,
    top_k: int = 5,
    min_confidence: float = 0.1,
    llm_provider: BaseProvider | None = None,
) -> list[SuggestedMethodology]:
    """Screen project against active methodologies and return ranked suggestions.

    Args:
        project_description: Raw text describing the project.
        project_input: Optional structured ProjectInput for enhanced matching.
        db: Methodology database (loads defaults if None).
        top_k: Maximum suggestions to return.
        min_confidence: Minimum confidence to include.

    Returns:
        Ranked list of SuggestedMethodology, highest confidence first.
    """
    if db is None:
        db = MethodologyDatabase()

    description_lower = project_description.lower()

    technology_type: str | None = None
    waste_types: list[str] | None = None
    user_methodology_ids: list[str] = []

    if project_input:
        technology_type = project_input.technology.technology_type
        waste_types = project_input.technology.waste_type
        user_methodology_ids = project_input.technology.methodology_ids

    scores: list[tuple[dict[str, Any], float, str]] = []

    for methodology in db.all_methodologies:
        tech_score = _score_technology_match(methodology, technology_type)
        waste_score = _score_waste_match(methodology, waste_types)
        category_score = _score_category_match(methodology, description_lower)
        condition_score = _score_applicability_conditions(methodology, description_lower)
        mention_score = _score_methodology_id_mentioned(methodology, description_lower)

        weights = {
            "technology": 0.25,
            "waste": 0.15,
            "category": 0.15,
            "conditions": 0.25,
            "mention": 0.20,
        }

        confidence = (
            tech_score * weights["technology"]
            + waste_score * weights["waste"]
            + category_score * weights["category"]
            + condition_score * weights["conditions"]
            + mention_score * weights["mention"]
        )

        rationale_parts = []
        if mention_score > 0:
            rationale_parts.append("methodology referenced in document")
        if tech_score > 0:
            rationale_parts.append(f"technology match ({technology_type})")
        if waste_score > 0:
            rationale_parts.append(f"waste type match ({waste_score:.0%})")
        if category_score > 0:
            rationale_parts.append("category keywords present")
        if condition_score > 0:
            rationale_parts.append(f"applicability conditions align ({condition_score:.0%})")

        if not rationale_parts:
            rationale_parts.append("low relevance to project description")

        rationale = "; ".join(rationale_parts)
        scores.append((methodology, confidence, rationale))

    scores.sort(key=lambda x: x[1], reverse=True)

    suggestions: list[SuggestedMethodology] = []
    for methodology, confidence, rationale in scores[:top_k]:
        if confidence < min_confidence:
            continue
        suggestions.append(
            SuggestedMethodology(
                methodology_id=methodology["id"],
                name=methodology["name"],
                confidence=round(confidence, 3),
                rationale=rationale,
                active_status_source=f"methodology_db ({db.data_version})",
                version=methodology.get("version"),
            )
        )

    if llm_provider is not None and suggestions:
        suggestions = _analyze_applicability_with_llm(
            project_description,
            suggestions,
            db,
            llm_provider,
            top_k=top_k,
            min_confidence=min_confidence,
        )

    if user_methodology_ids and suggestions:
        top_ids = {s.methodology_id for s in suggestions[:3]}
        for user_id in user_methodology_ids:
            if user_id not in top_ids and user_id != "UNKNOWN":
                logger.warning(
                    "user_methodology_not_top_match",
                    user_id=user_id,
                    top_suggestions=[s.methodology_id for s in suggestions[:3]],
                )

    logger.info(
        "screening_complete",
        total_methodologies=len(db.all_methodologies),
        suggestions=len(suggestions),
        top_id=suggestions[0].methodology_id if suggestions else None,
        data_version=db.data_version,
    )

    return suggestions


def _analyze_applicability_with_llm(
    project_description: str,
    candidates: list[SuggestedMethodology],
    db: MethodologyDatabase,
    provider: BaseProvider,
    *,
    top_k: int,
    min_confidence: float,
) -> list[SuggestedMethodology]:
    """Use an LLM to assess candidate applicability, falling back safely.

    The deterministic scorer limits the model to active database entries.  The
    model may re-rank and explain those entries but cannot invent methodology
    IDs or active-status claims.
    """
    candidate_by_id = {item.methodology_id: item for item in candidates}
    prompt = (
        "Assess methodology applicability for the project below. Return ONLY a JSON array "
        "of objects with methodology_id, confidence (0..1), and rationale. Do not introduce "
        "IDs outside CANDIDATES. Explain unmet or uncertain applicability conditions.\n\n"
        f"PROJECT:\n{project_description[:12000]}\n\n"
        f"CANDIDATES:\n{json.dumps([item.model_dump() for item in candidates], ensure_ascii=False)}"
    )
    result = provider.draft_section(
        section_id="methodology_screen",
        sub_section_id="applicability",
        prompt=prompt,
        provenance=[f"[METHODOLOGY DATABASE: {db.data_version}]"],
        max_chars=12000,
    )
    try:
        payload = _parse_json_array(result.text)
        analyzed: list[SuggestedMethodology] = []
        seen: set[str] = set()
        for item in payload:
            methodology_id = str(item["methodology_id"])
            if methodology_id in seen or methodology_id not in candidate_by_id:
                continue
            confidence = max(0.0, min(1.0, float(item["confidence"])))
            rationale = str(item["rationale"]).strip()
            if confidence < min_confidence or not rationale:
                continue
            original = candidate_by_id[methodology_id]
            analyzed.append(original.model_copy(update={
                "confidence": round(confidence, 3),
                "rationale": rationale,
                "active_status_source": f"LLM analysis; methodology_db ({db.data_version})",
            }))
            seen.add(methodology_id)
        if analyzed:
            analyzed.sort(key=lambda item: item.confidence, reverse=True)
            return analyzed[:top_k]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("llm_screening_parse_failed", provider=provider.name, error=str(exc))
    return candidates[:top_k]


def _parse_json_array(text: str) -> list[dict[str, Any]]:
    """Parse a JSON array, accepting a single Markdown JSON code fence."""
    value = text.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        value = "\n".join(lines[1:-1]).strip()
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
        raise ValueError("LLM screening response must be a JSON array of objects")
    return parsed
