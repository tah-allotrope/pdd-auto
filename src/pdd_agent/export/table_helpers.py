"""Low-level OOXML table primitives for VCS v4.4 DOCX export.

Adapted from patterns demonstrated in the Codex reference script,
but using the existing `_docx_attr()` lazy-import pattern for
late-bound python-docx imports.
"""

from __future__ import annotations

import importlib
from typing import Any


def _docx_attr(module_name: str, attr_name: str) -> Any:
    return getattr(importlib.import_module(module_name), attr_name)


def set_cell_shading(cell: Any, fill: str) -> None:
    """Set background colour of a table cell (hex string, e.g. 'D9EAF7')."""
    OxmlElement = _docx_attr("docx.oxml", "OxmlElement")
    qn = _docx_attr("docx.oxml.ns", "qn")
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margin(cell: Any, margin_twips: int = 90) -> None:
    """Set uniform internal margins for a table cell (default 90 twips ≈ 1.6 mm)."""
    OxmlElement = _docx_attr("docx.oxml", "OxmlElement")
    qn = _docx_attr("docx.oxml.ns", "qn")
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m in ("top", "start", "bottom", "end"):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(margin_twips))
        node.set(qn("w:type"), "dxa")


def set_cell_text(
    cell: Any,
    text: str,
    bold: bool = False,
    font_size: float = 9.0,
) -> None:
    """Write multi-line text into a cell, clearing existing content."""
    Pt = _docx_attr("docx.shared", "Pt")
    WD_ALIGN_VERTICAL = _docx_attr("docx.enum.table", "WD_ALIGN_VERTICAL")
    cell.text = ""
    lines = str(text).split("\n")
    for i, line in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(line)
        run.bold = bold
        run.font.size = Pt(font_size)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    set_cell_margin(cell)


def set_row_cant_split(row: Any) -> None:
    """Prevent a table row from splitting across pages."""
    OxmlElement = _docx_attr("docx.oxml", "OxmlElement")
    qn = _docx_attr("docx.oxml.ns", "qn")
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:cantSplit")) is None:
        tr_pr.append(OxmlElement("w:cantSplit"))


def set_row_repeat_header(row: Any) -> None:
    """Mark a table row as a repeating header row."""
    OxmlElement = _docx_attr("docx.oxml", "OxmlElement")
    qn = _docx_attr("docx.oxml.ns", "qn")
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:tblHeader")) is None:
        tr_pr.append(OxmlElement("w:tblHeader"))


def add_styled_table(
    doc: Any,
    rows: list[list[str]],
    widths: list[Any] | None = None,
    header: bool = True,
    font_size: float = 8.7,
) -> Any:
    """Add a uniformly styled table to the document.

    Args:
        doc: python-docx Document object.
        rows: List of row data; each row is a list of cell strings.
        widths: Optional list of column widths (e.g. Inches objects).
        header: If True, the first row is treated as a header.
        font_size: Font size in points for cell text.

    Returns:
        The created python-docx Table object.
    """
    if not rows:
        return None
    WD_TABLE_ALIGNMENT = _docx_attr("docx.enum.table", "WD_TABLE_ALIGNMENT")
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = True
    for r_idx, row in enumerate(rows):
        set_row_cant_split(table.rows[r_idx])
        if header and r_idx == 0:
            set_row_repeat_header(table.rows[r_idx])
        for c_idx, value in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            is_head = header and r_idx == 0
            set_cell_text(cell, value, bold=is_head, font_size=font_size)
            if is_head:
                set_cell_shading(cell, "D9EAF7")
            elif c_idx == 0 and len(row) == 2:
                set_cell_shading(cell, "F2F6FA")
    if widths:
        for row in table.rows:
            for idx, width in enumerate(widths):
                if idx < len(row.cells):
                    row.cells[idx].width = width
    doc.add_paragraph()
    return table
