"""DOCX export for structured, review-friendly Verra-style draft runs."""

from __future__ import annotations

from datetime import datetime
import importlib
import json
from dataclasses import dataclass, field
from pathlib import Path
import re
from types import SimpleNamespace
from typing import Any, Callable

import structlog
import yaml

from pdd_agent.llm.provider import DraftRun
from pdd_agent.review.consistency import check_quantitative_consistency
from pdd_agent.review.judge import _EVIDENCE_ID_RE
from schemas.project_input import ProjectInput
from pdd_agent.export.markdown_docx import render_markdown_body
from pdd_agent.export.assembly import canonical_subsection_title, strip_leading_title_heading
from pdd_agent.export.table_helpers import (
    add_styled_table,
)

logger = structlog.get_logger()

_DRAFT_RUNS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "runs"
_SCHEMA_PATH = Path(__file__).parent.parent.parent.parent / "schemas" / "pdd_section_schema.yaml"
_TEMPLATE_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "templates"
    / "VCS-Project-Description-Template-v4.4-FINAL2.docx"
)


class ExportBlockedError(Exception):
    """Raised when the export gate hard-blocks a run and force=False."""


@dataclass
class ExportGateResult:
    """Result of the pre-export tiered gate check."""

    blocked: bool
    hard_blocks: list[str] = field(default_factory=list)
    advisories: list[str] = field(default_factory=list)
    required_inputs: list[dict[str, str]] = field(default_factory=list)
    force_used: bool = False

    @property
    def passed(self) -> bool:
        return not self.blocked


def check_export_gate(
    run: DraftRun | dict[str, Any],
    project_input: ProjectInput | None = None,
    calc_result: Any | None = None,
    force: bool = False,
) -> ExportGateResult:
    """Run the tiered export gate against a DraftRun or its serialized dict.

    Hard-blocks (export refused unless ``force=True``):
      - Numbers contradicting ProjectInput / calc engine (via consistency.py)
      - Evidence citations to IDs not in the evidence registry

    Required inputs (export proceeds without ``--force``): every ``[MISSING]``
    marker in any section is collected into ``required_inputs`` and rendered
    as an "Appendix — Required Inputs" table — the model correctly reporting a
    missing input is honest behaviour, not a fabrication.

    Everything else exports as a watermarked DRAFT with advisory markers.
    """
    if isinstance(run, dict):
        sections_raw = run.get("sections", [])
        run_id = run.get("run_id", "unknown")
    else:
        sections_raw = run.sections
        run_id = run.run_id

    sections = [SimpleNamespace(**s) if isinstance(s, dict) else s for s in sections_raw]
    hard_blocks: list[str] = []
    advisories: list[str] = []
    required_inputs: list[dict[str, str]] = []

    consistency_report = check_quantitative_consistency(
        draft_sections=sections,
        project_input=project_input,
        run_id=run_id,
        calc_result=calc_result,
    )
    for flag in consistency_report.flags:
        if flag.severity == "CRITICAL":
            hard_blocks.append(f"[{flag.section_a}↔{flag.section_b}] {flag.message}")
        elif flag.severity == "HIGH":
            advisories.append(f"[{flag.section_a}↔{flag.section_b}] {flag.message}")

    _check_evidence_registry(sections, project_input, hard_blocks)
    _collect_required_inputs(sections, required_inputs)

    return ExportGateResult(
        blocked=bool(hard_blocks),
        hard_blocks=hard_blocks,
        advisories=advisories,
        required_inputs=required_inputs,
        force_used=force,
    )


def _check_evidence_registry(
    sections: list[Any],
    project_input: ProjectInput | None,
    hard_blocks: list[str],
) -> None:
    if project_input is None:
        return
    registry = getattr(project_input, "evidence_registry", None)
    if registry is None:
        return
    valid_numbers = {
        re.search(r"\d+", item.evidence_id).group()
        for item in getattr(registry, "items", [])
        if item.evidence_id
    }
    for section in sections:
        text = getattr(section, "text", "") or ""
        section_key = _gate_section_key(section)
        cited = set(_EVIDENCE_ID_RE.findall(text))
        invalid = sorted(cited - valid_numbers)
        if invalid:
            hard_blocks.append(
                f"[{section_key}] Cited evidence ID(s) not in registry: "
                f"{', '.join(f'E{e}' for e in invalid)}"
            )


def _collect_required_inputs(sections: list[Any], required_inputs: list[dict[str, str]]) -> None:
    """Collect every ``[MISSING]`` marker occurrence as a required-input entry.

    Mutates ``required_inputs`` in place; one entry per occurrence, in every
    section (not only Sections 3-4). Context is 200 whitespace-collapsed
    characters centred on the marker.
    """
    for section in sections:
        text = getattr(section, "text", "") or ""
        section_key = _gate_section_key(section)
        collapsed = " ".join(text.split())
        idx = collapsed.find("[MISSING]")
        while idx != -1:
            start = max(0, idx - 100)
            end = min(len(collapsed), idx + len("[MISSING]") + 100)
            required_inputs.append({"section_key": section_key, "context": collapsed[start:end]})
            idx = collapsed.find("[MISSING]", idx + 1)


def _gate_section_key(section: Any) -> str:
    ssid = getattr(section, "sub_section_id", "")
    if ssid:
        return str(ssid)
    return str(getattr(section, "section_id", ""))


def _docx_attr(module_name: str, attr_name: str) -> Any:
    return getattr(importlib.import_module(module_name), attr_name)


def export_run_to_docx(
    run_id: str,
    output_path: Path | None = None,
    project_name: str = "",
    project_input: ProjectInput | None = None,
    force: bool = False,
    runs_dir: Path | None = None,
    calc_result: Any | None = None,
) -> Path:
    """Export a DraftRun JSON to a review-friendly DOCX file.

    The export gate is evaluated before writing. Hard-blocks stop export unless
    ``force=True``; everything else exports as a watermarked DRAFT.

    ``runs_dir`` overrides the default ``data/runs`` directory used both to
    locate the run JSON and, when ``output_path`` is not given, to place the
    exported DOCX — callers with a redirected run persistence directory (e.g.
    the service's ``PDD_SERVICE_RUNS_DIR``) must pass it explicitly.

    ``calc_result`` defaults to whatever the run JSON's ``calc_result`` field
    carries (reconstructed via ``PddCalcResult.from_dict``); an explicit
    argument overrides that.
    """
    effective_runs_dir = runs_dir or _DRAFT_RUNS_DIR
    run_path = effective_runs_dir / f"{run_id}.json"
    if not run_path.exists():
        message = f"Draft run not found for run_id `{run_id}` at `{run_path}`"
        logger.error("draft_run_not_found", run_id=run_id, path=str(run_path))
        raise FileNotFoundError(message)

    try:
        Document = _docx_attr("docx", "Document")
    except ImportError as exc:
        message = (
            "python-docx is required for DOCX export. Install it with `pip install python-docx`."
        )
        logger.error("docx_dependency_missing", error=message)
        raise RuntimeError(message) from exc

    with open(run_path, encoding="utf-8") as handle:
        run_data = json.load(handle)

    from pdd_agent.calc.dispatch import PddCalcResult

    if calc_result is None:
        calc_result_dict = run_data.get("calc_result")
        calc_result_obj = PddCalcResult.from_dict(calc_result_dict) if calc_result_dict else None
    elif hasattr(calc_result, "to_dict"):
        calc_result_dict = calc_result.to_dict()
        calc_result_obj = calc_result
    else:
        calc_result_dict = calc_result
        calc_result_obj = PddCalcResult.from_dict(calc_result_dict) if calc_result_dict else None

    gate = check_export_gate(
        run_data, project_input=project_input, calc_result=calc_result_obj, force=force
    )
    if gate.blocked and not force:
        logger.error("export_gate_blocked", run_id=run_id, hard_blocks=gate.hard_blocks)
        raise ExportBlockedError(f"Export blocked for {run_id}. Hard blocks: {gate.hard_blocks}")
    if gate.blocked and force:
        logger.warning(
            "export_gate_forced",
            run_id=run_id,
            hard_blocks=gate.hard_blocks,
            message="Exporting with --force override; document is watermarked DRAFT.",
        )

    schema = _load_schema()
    sections = run_data.get("sections", [])
    display_math_sources: list[str] = []
    assumption_register = run_data.get("assumption_register") or {}
    blocked_items = assumption_register.get("guardrails", {}).get("blocked_review_items", [])
    blocked_paths = {item.get("field_path", ""): item.get("reason", "") for item in blocked_items}
    is_demo = run_data.get("provider") == "demo"

    if _TEMPLATE_PATH.exists():
        doc = Document(str(_TEMPLATE_PATH))
        _clear_body(doc)
    else:
        doc = Document()

    _set_base_styles(doc)

    resolved_project_name = project_name or run_data.get("project_name", "Unknown Project")
    _add_title_page(doc, resolved_project_name, run_id)
    _add_disclaimer(doc, is_demo=is_demo)
    _add_draft_watermark(doc, force=force, had_hard_blocks=gate.blocked)

    cover_data = run_data.get("structured_cover") or _infer_cover_data(run_data)
    render_cover_metadata_table(doc, cover_data)
    _add_audit_history_front_matter(doc, run_data, project_input)

    for sec_def in schema.get("sections", []):
        sid = sec_def["section_id"]
        section_heading = _section_heading(sec_def)
        doc.add_heading(section_heading, level=1)

        for sub_def in sec_def.get("sub_sections", []):
            ssid = sub_def["sub_section_id"]
            section = _find_section(sections, sid, ssid)
            subsection_heading = sub_def.get("heading", ssid)
            doc.add_heading(canonical_subsection_title(ssid, subsection_heading), level=2)

            if not section:
                _safe_paragraph_style(doc.add_paragraph("[Not drafted]"), "Intense Quote")
                continue

            _add_section_metadata(doc, section)
            # Strip title echo per S-3
            section_for_render = dict(section)
            try:
                section_for_render["text"] = strip_leading_title_heading(
                    section.get("text", ""), sub_def.get("heading", "")
                )
            except Exception:
                pass

            # PHASE-03 fix: structured_content used to *replace* the section's
            # prose (renderer called instead of the text paragraphs). Prose is
            # now rendered unconditionally first, and the table (when its
            # table_type resolves to a renderer) follows it.
            _add_section_prose(
                doc, section_for_render, is_demo, on_display_math=display_math_sources.append
            )

            structured = section.get("structured_content")
            if structured and isinstance(structured, dict):
                renderer = _TABLE_RENDERERS.get(structured.get("table_type", ""))
                if renderer:
                    renderer(doc, structured.get("data", {}))

            issues = section.get("issues", [])
            if issues and not is_demo:
                issue_intro = doc.add_paragraph()
                issue_intro.add_run("Review notes:").bold = True
                for issue in issues:
                    bullet = doc.add_paragraph()
                    _safe_paragraph_style(bullet, "List Bullet")
                    run = bullet.add_run(issue)
                    run.font.color.rgb = _docx_attr("docx.shared", "RGBColor")(0xB4, 0x23, 0x18)

    _add_assumption_appendix(doc, assumption_register, sections, blocked_paths, is_demo=is_demo)
    _add_calc_audit_appendix(doc, calc_result_dict)
    _add_formulas_appendix(doc, display_math_sources)
    _add_required_inputs_appendix(doc, gate.required_inputs)
    if not is_demo:
        # Document-level coherence findings (canonical source is run_review;
        # recompute here only for run files that predate it).
        if "document_coherence" not in run_data:
            try:
                from pdd_agent.review.document_coherence import check_document_coherence

                coherence = check_document_coherence(run_data)
                if coherence:
                    run_data = dict(run_data)
                    run_data["document_coherence"] = coherence
            except Exception:
                pass
        _add_reviewer_issues_appendix(doc, run_data, sections, blocked_paths, calc_result_dict)

    tbd_report = run_data.get("tbd")
    if tbd_report:
        render_tbd_appendix(doc, tbd_report)

    if project_input and getattr(project_input, "evidence_registry", None):
        _add_evidence_appendix(doc, project_input.evidence_registry)

    _add_page_numbers(doc)

    final_output = Path(output_path) if output_path else effective_runs_dir / f"{run_id}.docx"
    final_output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(final_output))
    logger.info("docx_exported", run_id=run_id, path=str(final_output))
    return final_output


# ─────────────────────────────────────────────
# Template helpers
# ─────────────────────────────────────────────


def _clear_body(doc: Any) -> None:
    """Remove all body paragraphs/tables but keep section properties (headers/footers)."""
    qn = _docx_attr("docx.oxml.ns", "qn")
    body = doc._body._element
    for child in list(body):
        if child.tag == qn("w:sectPr"):
            continue
        body.remove(child)


# ─────────────────────────────────────────────
# Style setup
# ─────────────────────────────────────────────


def _set_base_styles(doc: Any) -> None:
    Pt = _docx_attr("docx.shared", "Pt")
    Cm = _docx_attr("docx.shared", "Cm")
    qn = _docx_attr("docx.oxml.ns", "qn")

    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Arial"
    normal_style.font.size = Pt(9.5)
    if hasattr(normal_style, "_element") and normal_style._element.rPr is not None:
        rfonts = normal_style._element.rPr.rFonts
        if rfonts is not None:
            rfonts.set(qn("w:eastAsia"), "Arial")

    for style_name in ("Heading 1", "Heading 2", "Heading 3"):
        style = doc.styles[style_name]
        style.font.name = "Arial"
        style.font.bold = True

    for section in doc.sections:
        section.top_margin = Cm(1.7)
        section.bottom_margin = Cm(1.6)
        section.left_margin = Cm(1.8)
        section.right_margin = Cm(1.8)


# ─────────────────────────────────────────────
# Title / cover
# ─────────────────────────────────────────────


def _add_title_page(doc: Any, project_name: str, run_id: str) -> None:
    WD_ALIGN_PARAGRAPH = _docx_attr("docx.enum.text", "WD_ALIGN_PARAGRAPH")
    Pt = _docx_attr("docx.shared", "Pt")
    RGBColor = _docx_attr("docx.shared", "RGBColor")

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Project Design Document")
    run.bold = True
    run.font.size = Pt(20)
    run.font.color.rgb = RGBColor(31, 78, 121)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_run = subtitle.add_run("VCS Project Description - Template v4.4 draft")
    subtitle_run.font.size = Pt(14)

    project = doc.add_paragraph()
    project.alignment = WD_ALIGN_PARAGRAPH.CENTER
    project_run = project.add_run(project_name)
    project_run.bold = True
    project_run.font.size = Pt(15)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run(f"Run ID: {run_id}\n")
    meta.add_run(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    meta.add_run("Status: Internal review draft")
    doc.add_page_break()


def _add_disclaimer(doc: Any, is_demo: bool = False) -> None:
    RGBColor = _docx_attr("docx.shared", "RGBColor")
    paragraph = doc.add_paragraph()
    message = (
        "This document is a synthetic client-demo sample. "
        "It is intended for demonstration only and must not be treated as verified project evidence or a final audited Verra filing."
        if is_demo
        else "Internal draft for review; contains synthetic assumptions for missing project data. Do not treat this document as a final audited Verra filing."
    )
    run = paragraph.add_run(message)
    run.bold = True
    run.font.color.rgb = RGBColor(0x9C, 0x00, 0x06)
    _highlight_paragraph(paragraph, "FCE4D6")


def _add_draft_watermark(doc: Any, force: bool = False, had_hard_blocks: bool = False) -> None:
    """Add a prominent DRAFT stamp to every exported DOCX.

    The ``(EXPORT GATE OVERRIDE)`` suffix appears only when the caller forced
    past an export gate that actually hard-blocked — a forced export of a run
    whose only finding is ``[MISSING]`` markers is not an override.
    """
    WD_ALIGN_PARAGRAPH = _docx_attr("docx.enum.text", "WD_ALIGN_PARAGRAPH")
    Pt = _docx_attr("docx.shared", "Pt")
    RGBColor = _docx_attr("docx.shared", "RGBColor")

    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    message = "DRAFT — NOT FOR FILING"
    if force and had_hard_blocks:
        message += " (EXPORT GATE OVERRIDE)"
    run = paragraph.add_run(message)
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)


# ─────────────────────────────────────────────
# Table renderers
# ─────────────────────────────────────────────


def render_cover_metadata_table(doc: Any, data: dict[str, Any]) -> Any:
    Inches = _docx_attr("docx.shared", "Inches")
    rows = [
        ["Project title", data.get("project_title", "-")],
        ["Project ID", data.get("project_id", "-")],
        ["Crediting period", data.get("crediting_period", "-")],
        ["Original date of issue", data.get("original_issue_date", "-")],
        ["Most recent date of issue", data.get("most_recent_issue_date", "-")],
        ["Version", data.get("version", "-")],
        ["VCS Standard Version", data.get("vcs_standard_version", "-")],
        ["Prepared by", data.get("prepared_by", "-")],
    ]
    return add_styled_table(
        doc, rows, widths=[Inches(2.2), Inches(4.8)], header=False, font_size=9.3
    )


def render_audit_history_table(doc: Any, data: dict[str, Any]) -> Any:
    Inches = _docx_attr("docx.shared", "Inches")
    rows = [["Audit type", "Period", "Program", "Validation/verification body name", "Years"]]
    for entry in data.get("audits", []):
        rows.append(
            [
                str(entry.get("audit_type", "-")),
                str(entry.get("period", "-")),
                str(entry.get("program", "-")),
                str(entry.get("vvb_name", "-")),
                str(entry.get("number_of_years", "-")),
            ]
        )
    return add_styled_table(
        doc,
        rows,
        widths=[Inches(1.1), Inches(1.7), Inches(0.8), Inches(1.7), Inches(0.6)],
        header=True,
    )


def render_proponent_table(doc: Any, data: dict[str, Any]) -> Any:
    Inches = _docx_attr("docx.shared", "Inches")
    rows = [
        ["Organization name", data.get("org_name", "-")],
        ["Contact person", data.get("contact_name", "-")],
        ["Title", data.get("title", "-")],
        ["Address", data.get("address", "-")],
        ["Telephone", data.get("telephone", "-")],
        ["Email", data.get("email", "-")],
    ]
    return add_styled_table(
        doc, rows, widths=[Inches(1.7), Inches(5.4)], header=False, font_size=9.0
    )


def render_ghg_boundary_table(doc: Any, data: dict[str, Any]) -> Any:
    Inches = _docx_attr("docx.shared", "Inches")
    rows = [["Scenario", "Source", "Gas", "Included?", "Justification"]]
    for entry in data.get("entries", []):
        rows.append(
            [
                str(entry.get("scenario", "-")),
                str(entry.get("source", "-")),
                str(entry.get("gas", "-")),
                str(entry.get("included", "-")),
                str(entry.get("justification", "-")),
            ]
        )
    return add_styled_table(
        doc,
        rows,
        widths=[Inches(0.8), Inches(2.2), Inches(0.7), Inches(0.8), Inches(2.6)],
        header=True,
        font_size=7.2,
    )


def render_applicability_table(doc: Any, data: dict[str, Any]) -> Any:
    Inches = _docx_attr("docx.shared", "Inches")
    rows = [["Methodology/tool", "Applicability condition", "Justification of compliance"]]
    for entry in data.get("entries", []):
        rows.append(
            [
                str(entry.get("methodology", "-")),
                str(entry.get("condition", "-")),
                str(entry.get("justification", "-")),
            ]
        )
    return add_styled_table(
        doc, rows, widths=[Inches(1.0), Inches(3.1), Inches(3.0)], header=True, font_size=7.6
    )


def render_monitoring_fixed_params_table(doc: Any, data: dict[str, Any]) -> Any:
    Inches = _docx_attr("docx.shared", "Inches")
    rows = [["Data/parameter", "Unit", "Description", "Value", "Source", "Comments"]]
    for entry in data.get("entries", []):
        rows.append(
            [
                str(entry.get("parameter", "-")),
                str(entry.get("unit", "-")),
                str(entry.get("description", "-")),
                str(entry.get("value", "-")),
                str(entry.get("source", "-")),
                str(entry.get("comments", "-")),
            ]
        )
    return add_styled_table(
        doc,
        rows,
        widths=[Inches(1.4), Inches(0.8), Inches(2.2), Inches(1.0), Inches(1.2), Inches(1.0)],
        header=True,
        font_size=8.0,
    )


def render_monitoring_tracked_params_table(doc: Any, data: dict[str, Any]) -> Any:
    Inches = _docx_attr("docx.shared", "Inches")
    rows = [["Data/parameter", "Unit", "Description", "Frequency", "Equipment", "QA/QC"]]
    for entry in data.get("entries", []):
        rows.append(
            [
                str(entry.get("parameter", "-")),
                str(entry.get("unit", "-")),
                str(entry.get("description", "-")),
                str(entry.get("frequency", "-")),
                str(entry.get("equipment", "-")),
                str(entry.get("qa_qc", "-")),
            ]
        )
    return add_styled_table(
        doc,
        rows,
        widths=[Inches(1.4), Inches(0.8), Inches(2.2), Inches(1.0), Inches(1.2), Inches(1.0)],
        header=True,
        font_size=8.0,
    )


def render_risk_assessment_table(doc: Any, data: dict[str, Any]) -> Any:
    Inches = _docx_attr("docx.shared", "Inches")
    rows = [["Risk category", "Risks identified", "Mitigation or preventative measure(s) taken"]]
    for entry in data.get("entries", []):
        rows.append(
            [
                str(entry.get("category", "-")),
                str(entry.get("risks", "-")),
                str(entry.get("mitigation", "-")),
            ]
        )
    return add_styled_table(
        doc, rows, widths=[Inches(1.6), Inches(2.5), Inches(3.0)], header=True, font_size=8.0
    )


def render_emissions_summary_table(doc: Any, data: dict[str, Any]) -> Any:
    Inches = _docx_attr("docx.shared", "Inches")
    rows = [
        [
            "Calendar year of crediting period",
            "Estimated GHG emission reductions or removals (tCO2e)",
        ]
    ]
    for entry in data.get("entries", []):
        rows.append(
            [
                str(entry.get("period", "-")),
                str(entry.get("value", "-")),
            ]
        )
    if data.get("total"):
        rows.append(["Total", str(data["total"])])
    return add_styled_table(
        doc, rows, widths=[Inches(3.1), Inches(3.0)], header=True, font_size=8.5
    )


def render_sustainable_development_table(doc: Any, data: dict[str, Any]) -> Any:
    Inches = _docx_attr("docx.shared", "Inches")
    rows = [["Sustainable development area", "Project contribution", "Monitoring approach"]]
    for entry in data.get("entries", []):
        rows.append(
            [
                str(entry.get("area", "-")),
                str(entry.get("contribution", "-")),
                str(entry.get("monitoring", "-")),
            ]
        )
    return add_styled_table(
        doc, rows, widths=[Inches(1.7), Inches(3.0), Inches(2.4)], header=True, font_size=8.0
    )


def render_data_gaps_table(doc: Any, data: dict[str, Any]) -> Any:
    Inches = _docx_attr("docx.shared", "Inches")
    rows = [["Topic", "Gap/assumption", "Needed evidence"]]
    for entry in data.get("entries", []):
        rows.append(
            [
                str(entry.get("topic", "-")),
                str(entry.get("gap", "-")),
                str(entry.get("evidence", "-")),
            ]
        )
    return add_styled_table(
        doc, rows, widths=[Inches(1.5), Inches(3.0), Inches(2.6)], header=True, font_size=8.0
    )


def render_tbd_appendix(doc: Any, tbd_report: dict[str, Any]) -> Any:
    Inches = _docx_attr("docx.shared", "Inches")
    doc.add_page_break()
    doc.add_heading("Appendix C - Data Gaps and Evidence Requirements", level=1)
    items = tbd_report.get("items", [])
    if not items:
        doc.add_paragraph("No TBD markers were detected in this draft.")
        return None
    rows = [["Section", "Marker", "Context", "Suggested evidence"]]
    for item in items:
        sid = item.get("section_id", "")
        ssid = item.get("sub_section_id", "")
        section_label = f"{sid}.{ssid}" if ssid else sid
        rows.append(
            [
                section_label,
                str(item.get("marker", "-")),
                str(item.get("context", "-")),
                str(item.get("evidence_type", "-")),
            ]
        )
    return add_styled_table(
        doc,
        rows,
        widths=[Inches(1.0), Inches(1.5), Inches(2.5), Inches(2.1)],
        header=True,
        font_size=8.0,
    )


def _add_evidence_appendix(doc: Any, registry: Any) -> None:
    """Render the evidence registry as an appendix table in the DOCX."""
    Inches = _docx_attr("docx.shared", "Inches")
    items = getattr(registry, "items", [])
    if not items:
        return

    doc.add_page_break()
    doc.add_heading("Appendix D - Evidence Registry", level=1)
    doc.add_paragraph(
        "The following evidence items were registered during project intake. "
        "Each item is assigned a unique ID (E001, E002, ...) that can be cited "
        "in the PDD draft using [E###] markers."
    )

    rows = [["ID", "Source type", "Description", "Section ref"]]
    for item in items:
        eid = getattr(item, "evidence_id", "?")
        source_type = getattr(item, "source_type", "unknown")
        description = getattr(item, "description", "")
        section_ref = getattr(item, "section_ref", "-") or "-"
        rows.append([eid, source_type, description, section_ref])

    add_styled_table(
        doc,
        rows,
        widths=[Inches(0.8), Inches(1.2), Inches(3.5), Inches(1.0)],
        header=True,
        font_size=8.0,
    )


_TABLE_RENDERERS: dict[str, Any] = {
    "cover_metadata": render_cover_metadata_table,
    "audit_history": render_audit_history_table,
    "proponent": render_proponent_table,
    "ghg_boundary": render_ghg_boundary_table,
    "applicability": render_applicability_table,
    "monitoring_fixed_params": render_monitoring_fixed_params_table,
    "monitoring_tracked_params": render_monitoring_tracked_params_table,
    "risk_assessment": render_risk_assessment_table,
    "emissions_summary": render_emissions_summary_table,
    "sustainable_development": render_sustainable_development_table,
    "data_gaps": render_data_gaps_table,
}


# ─────────────────────────────────────────────
# Legacy / metadata helpers
# ─────────────────────────────────────────────


def _safe_set_table_style(
    table: Any, preferred: str = "Light Grid Accent 1", fallback: str = "Table Grid"
) -> None:
    """Set table style, falling back if the preferred style is missing."""
    try:
        table.style = preferred
    except KeyError:
        table.style = fallback


def _safe_paragraph_style(paragraph: Any, style_name: str) -> None:
    """Apply a paragraph style safely, ignoring if the style is missing."""
    try:
        paragraph.style = style_name
    except KeyError:
        pass


def _add_cover_metadata(doc: Any, run_data: dict[str, Any]) -> None:
    WD_TABLE_ALIGNMENT = _docx_attr("docx.enum.table", "WD_TABLE_ALIGNMENT")
    table = doc.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _safe_set_table_style(table)
    rows = [
        ("Project", run_data.get("project_name", "-")),
        ("Provider", run_data.get("provider", "noop")),
        ("Draft sections", str(len(run_data.get("sections", [])))),
        (
            "Assumption register attached",
            "yes" if run_data.get("assumption_register") else "no",
        ),
    ]
    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = value
        cells[0].paragraphs[0].runs[0].bold = True
    doc.add_page_break()


def _infer_cover_data(run_data: dict[str, Any]) -> dict[str, Any]:
    """Best-effort cover metadata from a legacy run JSON."""
    return {
        "project_title": run_data.get("project_name", "Unknown Project"),
        "project_id": run_data.get("project_id_vcs", "-"),
        "crediting_period": "-",
        "original_issue_date": "-",
        "most_recent_issue_date": datetime.now().strftime("%d-%B-%Y"),
        "version": "Draft 0.1",
        "vcs_standard_version": "-",
        "prepared_by": "-",
    }


def _add_section_metadata(doc: Any, section: dict[str, Any]) -> None:
    WD_TABLE_ALIGNMENT = _docx_attr("docx.enum.table", "WD_TABLE_ALIGNMENT")
    meta = doc.add_table(rows=2, cols=2)
    _safe_set_table_style(meta)
    meta.alignment = WD_TABLE_ALIGNMENT.LEFT
    rows = [
        ("Confidence", section.get("confidence", "UNKNOWN")),
        (
            "Sources",
            _format_source_counts(section.get("fact_provenance", [])),
        ),
    ]
    for index, (label, value) in enumerate(rows):
        meta.rows[index].cells[0].text = label
        meta.rows[index].cells[1].text = value
        meta.rows[index].cells[0].paragraphs[0].runs[0].bold = True

    provenance = section.get("provenance", [])
    if provenance:
        prov = doc.add_paragraph()
        _safe_paragraph_style(prov, "Quote")
        prov.add_run("Retrieved provenance: ").bold = True
        prov.add_run("; ".join(provenance))

    synthetic_uses = section.get("synthetic_uses", [])
    if synthetic_uses:
        note = doc.add_paragraph()
        _safe_paragraph_style(note, "Quote")
        note.add_run("Assumption note: ").bold = True
        note.add_run(
            f"{len(synthetic_uses)} synthetic/demo-backed input(s) affect this section. "
            "See Assumption Appendix for field-level details."
        )


def _add_assumption_appendix(
    doc: Any,
    assumption_register: dict[str, Any],
    sections: list[dict[str, Any]],
    blocked_paths: dict[str, str],
    is_demo: bool = False,
) -> None:
    doc.add_page_break()
    doc.add_heading(
        "Appendix A - Assumption Summary" if is_demo else "Appendix A - Assumption Register",
        level=1,
    )

    assumptions = assumption_register.get("assumptions", []) if assumption_register else []
    if not assumptions:
        doc.add_paragraph("No assumption register was attached to this run.")
        return

    usage_map = _build_usage_map(sections)
    table = doc.add_table(rows=1, cols=4 if is_demo else 6)
    _safe_set_table_style(table)
    headers = (
        ["Field", "Source Type", "Confidence", "Value"]
        if is_demo
        else ["Field", "Source Type", "Confidence", "Value", "Affects", "Review Gate"]
    )
    for index, header in enumerate(headers):
        table.rows[0].cells[index].text = header
        table.rows[0].cells[index].paragraphs[0].runs[0].bold = True

    for item in assumptions:
        cells = table.add_row().cells
        field_path = item.get("field_path", "")
        cells[0].text = field_path
        cells[1].text = str(item.get("source_type", ""))
        cells[2].text = str(item.get("confidence", ""))
        cells[3].text = _truncate_value(item.get("value"))
        if not is_demo:
            cells[4].text = ", ".join(usage_map.get(field_path, [])) or "-"
            cells[5].text = blocked_paths.get(field_path, "-")

    notes = assumption_register.get("guardrails", {}).get("notes", [])
    if notes:
        doc.add_paragraph()
        doc.add_paragraph("Assumption guardrails:").runs[0].bold = True
        for note in notes:
            p = doc.add_paragraph(note)
            _safe_paragraph_style(p, "List Bullet")


def _add_calc_audit_appendix(doc: Any, calc_result: dict[str, Any] | None) -> None:
    """Render the quantification audit-trail appendix from a calc_result dict.

    No-op when calc_result is None — most legacy runs (demo/noop, or any run
    predating calc persistence) have no calc result to render.
    """
    if not calc_result:
        return

    doc.add_page_break()
    doc.add_heading("Appendix — Quantification Audit Trail", level=1)
    doc.add_paragraph(f"Methodology: {calc_result.get('methodology_id', '')}")

    table = doc.add_table(rows=1, cols=4)
    _safe_set_table_style(table)
    headers = ["Component", "Value (tCO2e/yr)", "Unit", "Formula reference"]
    for index, header in enumerate(headers):
        table.rows[0].cells[index].text = header
        table.rows[0].cells[index].paragraphs[0].runs[0].bold = True

    for comp in calc_result.get("components", []):
        cells = table.add_row().cells
        cells[0].text = str(comp.get("name", ""))
        cells[1].text = f"{comp.get('value_tco2e', 0.0):,.2f}"
        cells[2].text = str(comp.get("unit", ""))
        cells[3].text = str(comp.get("formula", ""))


def _add_reviewer_issues_appendix(
    doc: Any,
    run_data: dict[str, Any],
    sections: list[dict[str, Any]],
    blocked_paths: dict[str, str],
    calc_result: dict[str, Any] | None = None,
) -> None:
    doc.add_page_break()
    doc.add_heading("Appendix B - Reviewer Issues", level=1)

    calc_warnings = (calc_result or {}).get("warnings", [])
    flagged_sections = [
        section for section in sections if section.get("issues") or section.get("synthetic_uses")
    ]
    if not flagged_sections and not calc_warnings:
        doc.add_paragraph("No reviewer issues were recorded.")
        return

    if calc_warnings:
        doc.add_heading("Calculation Engine", level=2)
        for warning in calc_warnings:
            p = doc.add_paragraph(f"CALC: {warning}")
            _safe_paragraph_style(p, "List Bullet")

    if not flagged_sections:
        return

    summary = doc.add_table(rows=1, cols=5)
    _safe_set_table_style(summary)
    headers = ["Section", "Confidence", "Review Sensitivity", "Issue Count", "Blocked Inputs"]
    for index, header in enumerate(headers):
        summary.rows[0].cells[index].text = header
        summary.rows[0].cells[index].paragraphs[0].runs[0].bold = True

    for section in flagged_sections:
        blocked = [
            item.get("field_path", "")
            for item in section.get("synthetic_uses", [])
            if item.get("field_path") in blocked_paths
        ]
        cells = summary.add_row().cells
        cells[0].text = _section_key(section)
        cells[1].text = section.get("confidence", "UNKNOWN")
        cells[2].text = section.get("review_sensitivity", "LOW")
        cells[3].text = str(len(section.get("issues", [])))
        cells[4].text = ", ".join(blocked) or "-"

    for section in flagged_sections:
        doc.add_heading(_section_key(section), level=2)
        if section.get("issues"):
            for issue in section.get("issues", []):
                p = doc.add_paragraph(issue)
                _safe_paragraph_style(p, "List Bullet")
        blocked = [
            item.get("field_path", "")
            for item in section.get("synthetic_uses", [])
            if item.get("field_path") in blocked_paths
        ]
        if blocked:
            paragraph = doc.add_paragraph()
            paragraph.add_run("Blocked review inputs: ").bold = True
            paragraph.add_run(", ".join(blocked))

    # Document-level coherence findings
    doc_coherence = run_data.get("document_coherence", [])
    if doc_coherence:
        doc.add_heading("Document-level findings", level=2)
        for finding in doc_coherence:
            p = doc.add_paragraph(
                f"{finding.get('check', '')}: {finding.get('detail', '')} (sections: {', '.join(finding.get('sections', []))})"
            )
            _safe_paragraph_style(p, "List Bullet")


def _find_section(
    sections: list[dict[str, Any]], section_id: str, sub_section_id: str
) -> dict[str, Any] | None:
    return next(
        (
            section
            for section in sections
            if section.get("section_id") == section_id
            and section.get("sub_section_id") == sub_section_id
        ),
        None,
    )


def _section_heading(section_def: dict[str, Any]) -> str:
    section_id = section_def.get("section_id", "")
    canonical = section_def.get("canonical_heading", f"Section {section_id}")
    return f"{section_id} {canonical}".strip()


def _section_key(section: dict[str, Any]) -> str:
    return section.get("sub_section_id") or section.get("section_id", "")


def _format_source_counts(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "none"
    counts: dict[str, int] = {}
    for entry in entries:
        key = str(entry.get("source_type", "unknown"))
        counts[key] = counts.get(key, 0) + 1
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def _build_usage_map(sections: list[dict[str, Any]]) -> dict[str, list[str]]:
    usage: dict[str, list[str]] = {}
    for section in sections:
        section_key = _section_key(section)
        for item in section.get("synthetic_uses", []):
            field_path = item.get("field_path")
            if not field_path:
                continue
            usage.setdefault(field_path, [])
            if section_key not in usage[field_path]:
                usage[field_path].append(section_key)
    return usage


def _truncate_value(value: Any, limit: int = 80) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def _add_section_prose(
    doc: Any,
    section: dict[str, Any],
    is_demo: bool,
    on_display_math: Callable[[str], None] | None = None,
) -> None:
    """Append a section's narrative paragraphs (or a placeholder when empty).

    Extracted from the two identical arms of the old structured/unstructured
    dispatch (PHASE-03 of the 2026-08-13 grounding-rebuild plan) so prose
    renders unconditionally, independent of whether a table follows it.

    Since the 2026-08-21 real-output-fidelity plan the body is rendered by
    ``render_markdown_body`` so real model Markdown (headings, pipe tables,
    emphasis, lists, math) becomes native Word content instead of literal
    artifact characters.
    """
    text = section.get("text", "")
    if not text:
        _safe_paragraph_style(doc.add_paragraph("[No content drafted yet]"), "Intense Quote")
        return
    paragraphs_before = len(doc.paragraphs)
    render_markdown_body(doc, text, on_display_math=on_display_math)
    if not is_demo and section.get("confidence") in {"LOW", "UNSUPPORTED"}:
        for paragraph in doc.paragraphs[paragraphs_before:]:
            _highlight_paragraph(paragraph, "FFF2CC")


def _add_required_inputs_appendix(doc: Any, required_inputs: list[dict[str, str]]) -> None:
    """Append an "Appendix — Required Inputs" table; no-op when empty.

    Capped at the first 100 entries so a noop-provider run full of markers
    cannot produce an unbounded appendix.
    """
    if not required_inputs:
        return
    doc.add_heading("Appendix — Required Inputs", level=1)
    doc.add_paragraph(
        "The drafting model flagged the following facts as missing from the project "
        "inputs. Each entry needs a human-supplied value before filing."
    )
    rendered = required_inputs[:100]
    rows = [["Section", "What is missing"]]
    for item in rendered:
        rows.append([item.get("section_key", ""), item.get("context", "")])
    if len(required_inputs) > 100:
        rows.append(
            ["", f"… and {len(required_inputs) - 100} more required inputs (see the run JSON)"]
        )
    add_styled_table(doc, rows, widths=None, header=True, font_size=8.7)


def _add_formulas_appendix(doc: Any, formulas: list[str]) -> None:
    """Append an "Appendix — Formulas (verbatim source)" section; no-op when empty."""
    if not formulas:
        return
    doc.add_heading("Appendix — Formulas (verbatim source)", level=1)
    for formula in formulas:
        paragraph = doc.add_paragraph()
        run = paragraph.add_run(formula)
        run.font.name = "Consolas"
        run.font.size = _docx_attr("docx.shared", "Pt")(9)


def _add_audit_history_front_matter(
    doc: Any, run_data: dict[str, Any], project_input: ProjectInput | None
) -> None:
    """Render an "Audit History" heading and table as front matter.

    No-op (adds no heading) when project_input is None or carries no
    audit_history entries.
    """
    if project_input is None:
        return
    audit_history = getattr(project_input.project, "audit_history", None)
    if not audit_history:
        return
    doc.add_heading("Audit History", level=2)
    render_audit_history_table(
        doc,
        {
            "audits": [
                {
                    "audit_type": entry.audit_type,
                    "period": entry.period,
                    "program": entry.program,
                    "vvb_name": entry.vvb_name,
                    "number_of_years": entry.number_of_years,
                }
                for entry in audit_history
            ]
        },
    )


def _split_paragraphs(text: str) -> list[str]:
    """Split text into non-empty stripped lines.

    Deliberately Markdown-naive: this helper is kept only for call sites that
    render short single-purpose strings. Section bodies must go through
    ``render_markdown_body`` instead.
    """
    pieces = [piece.strip() for piece in text.split("\n")]
    return [piece for piece in pieces if piece]


def _highlight_paragraph(paragraph: Any, fill: str) -> None:
    OxmlElement = _docx_attr("docx.oxml", "OxmlElement")
    qn = _docx_attr("docx.oxml.ns", "qn")

    for run in paragraph.runs:
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), fill)
        run._r.get_or_add_rPr().append(shading)


def _add_page_numbers(doc: Any) -> None:
    OxmlElement = _docx_attr("docx.oxml", "OxmlElement")
    qn = _docx_attr("docx.oxml.ns", "qn")

    for section in doc.sections:
        footer = section.footer
        footer.is_linked_to_previous = False
        paragraph = footer.paragraphs[0]
        paragraph.alignment = 1
        run = paragraph.add_run()
        fld_char_begin = OxmlElement("w:fldChar")
        fld_char_begin.set(qn("w:fldCharType"), "begin")
        instr_text = OxmlElement("w:instrText")
        instr_text.set(qn("xml:space"), "preserve")
        instr_text.text = "PAGE"
        fld_char_sep = OxmlElement("w:fldChar")
        fld_char_sep.set(qn("w:fldCharType"), "separate")
        fld_char_end = OxmlElement("w:fldChar")
        fld_char_end.set(qn("w:fldCharType"), "end")
        run._r.append(fld_char_begin)
        run._r.append(instr_text)
        run._r.append(fld_char_sep)
        run._r.append(fld_char_end)


def _load_schema() -> dict[str, Any]:
    with open(_SCHEMA_PATH, encoding="utf-8") as handle:
        return yaml.safe_load(handle)
