"""DOCX export for structured, review-friendly Verra-style draft runs."""

from __future__ import annotations

from datetime import datetime
import importlib
import json
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()

_DRAFT_RUNS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "runs"
_SCHEMA_PATH = Path(__file__).parent.parent.parent.parent / "schemas" / "pdd_section_schema.yaml"


def _docx_attr(module_name: str, attr_name: str) -> Any:
    return getattr(importlib.import_module(module_name), attr_name)


def export_run_to_docx(
    run_id: str,
    output_path: Path | None = None,
    project_name: str = "",
) -> Path:
    """Export a DraftRun JSON to a review-friendly DOCX file."""
    run_path = _DRAFT_RUNS_DIR / f"{run_id}.json"
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

    schema = _load_schema()
    sections = run_data.get("sections", [])
    assumption_register = run_data.get("assumption_register") or {}
    blocked_items = assumption_register.get("guardrails", {}).get("blocked_review_items", [])
    blocked_paths = {item.get("field_path", ""): item.get("reason", "") for item in blocked_items}

    doc = Document()
    _set_base_styles(doc)

    resolved_project_name = project_name or run_data.get("project_name", "Unknown Project")
    _add_title_page(doc, resolved_project_name, run_id)
    _add_disclaimer(doc)
    _add_cover_metadata(doc, run_data)

    for sec_def in schema.get("sections", []):
        sid = sec_def["section_id"]
        section_heading = _section_heading(sec_def)
        doc.add_heading(section_heading, level=1)

        for sub_def in sec_def.get("sub_sections", []):
            ssid = sub_def["sub_section_id"]
            section = _find_section(sections, sid, ssid)
            subsection_heading = sub_def.get("heading", ssid)
            doc.add_heading(subsection_heading, level=2)

            if not section:
                doc.add_paragraph("[Not drafted]").style = "Intense Quote"
                continue

            _add_section_metadata(doc, section)
            text = section.get("text", "")
            if text:
                for paragraph_text in _split_paragraphs(text):
                    paragraph = doc.add_paragraph(paragraph_text)
                    if section.get("confidence") in {"LOW", "UNSUPPORTED"}:
                        _highlight_paragraph(paragraph, "FFF2CC")
            else:
                doc.add_paragraph("[No content drafted yet]").style = "Intense Quote"

            issues = section.get("issues", [])
            if issues:
                issue_intro = doc.add_paragraph()
                issue_intro.add_run("Review notes:").bold = True
                for issue in issues:
                    bullet = doc.add_paragraph(style="List Bullet")
                    run = bullet.add_run(issue)
                    run.font.color.rgb = _docx_attr("docx.shared", "RGBColor")(0xB4, 0x23, 0x18)

    _add_assumption_appendix(doc, assumption_register, sections, blocked_paths)
    _add_reviewer_issues_appendix(doc, run_data, sections, blocked_paths)
    _add_page_numbers(doc)

    final_output = Path(output_path) if output_path else _DRAFT_RUNS_DIR / f"{run_id}.docx"
    final_output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(final_output))
    logger.info("docx_exported", run_id=run_id, path=str(final_output))
    return final_output


def _set_base_styles(doc: Any) -> None:
    Pt = _docx_attr("docx.shared", "Pt")
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(10.5)
    for style_name in ("Heading 1", "Heading 2", "Heading 3"):
        style = doc.styles[style_name]
        style.font.name = "Calibri"
        style.font.bold = True


def _add_title_page(doc: Any, project_name: str, run_id: str) -> None:
    WD_ALIGN_PARAGRAPH = _docx_attr("docx.enum.text", "WD_ALIGN_PARAGRAPH")
    Pt = _docx_attr("docx.shared", "Pt")

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Project Design Document")
    run.bold = True
    run.font.size = Pt(22)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_run = subtitle.add_run("Verra-style Waste-to-Energy Draft")
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


def _add_disclaimer(doc: Any) -> None:
    RGBColor = _docx_attr("docx.shared", "RGBColor")
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(
        "Internal draft for review; contains synthetic assumptions for missing project data. "
        "Do not treat this document as a final audited Verra filing."
    )
    run.bold = True
    run.font.color.rgb = RGBColor(0x9C, 0x00, 0x06)
    _highlight_paragraph(paragraph, "FCE4D6")


def _add_cover_metadata(doc: Any, run_data: dict[str, Any]) -> None:
    WD_TABLE_ALIGNMENT = _docx_attr("docx.enum.table", "WD_TABLE_ALIGNMENT")
    table = doc.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Light Grid Accent 1"
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


def _add_section_metadata(doc: Any, section: dict[str, Any]) -> None:
    WD_TABLE_ALIGNMENT = _docx_attr("docx.enum.table", "WD_TABLE_ALIGNMENT")
    meta = doc.add_table(rows=2, cols=2)
    meta.style = "Light Grid Accent 1"
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
        prov = doc.add_paragraph(style="Quote")
        prov.add_run("Retrieved provenance: ").bold = True
        prov.add_run("; ".join(provenance))

    synthetic_uses = section.get("synthetic_uses", [])
    if synthetic_uses:
        note = doc.add_paragraph(style="Quote")
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
) -> None:
    doc.add_page_break()
    doc.add_heading("Appendix A - Assumption Register", level=1)

    assumptions = assumption_register.get("assumptions", []) if assumption_register else []
    if not assumptions:
        doc.add_paragraph("No assumption register was attached to this run.")
        return

    usage_map = _build_usage_map(sections)
    table = doc.add_table(rows=1, cols=6)
    table.style = "Light Grid Accent 1"
    headers = ["Field", "Source Type", "Confidence", "Value", "Affects", "Review Gate"]
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
        cells[4].text = ", ".join(usage_map.get(field_path, [])) or "-"
        cells[5].text = blocked_paths.get(field_path, "-")

    notes = assumption_register.get("guardrails", {}).get("notes", [])
    if notes:
        doc.add_paragraph()
        doc.add_paragraph("Assumption guardrails:").runs[0].bold = True
        for note in notes:
            doc.add_paragraph(note, style="List Bullet")


def _add_reviewer_issues_appendix(
    doc: Any,
    run_data: dict[str, Any],
    sections: list[dict[str, Any]],
    blocked_paths: dict[str, str],
) -> None:
    doc.add_page_break()
    doc.add_heading("Appendix B - Reviewer Issues", level=1)

    flagged_sections = [
        section for section in sections if section.get("issues") or section.get("synthetic_uses")
    ]
    if not flagged_sections:
        doc.add_paragraph("No reviewer issues were recorded.")
        return

    summary = doc.add_table(rows=1, cols=5)
    summary.style = "Light Grid Accent 1"
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
                doc.add_paragraph(issue, style="List Bullet")
        blocked = [
            item.get("field_path", "")
            for item in section.get("synthetic_uses", [])
            if item.get("field_path") in blocked_paths
        ]
        if blocked:
            paragraph = doc.add_paragraph()
            paragraph.add_run("Blocked review inputs: ").bold = True
            paragraph.add_run(", ".join(blocked))


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


def _split_paragraphs(text: str) -> list[str]:
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
