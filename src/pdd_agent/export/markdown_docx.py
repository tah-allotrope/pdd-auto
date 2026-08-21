"""Markdown block scanner that renders real model output into python-docx.

Implements Specification S-1 of the 2026-08-21 real-output-fidelity plan:
a small, dependency-free CommonMark-ish scanner (fenced code, ATX headings,
display math, pipe tables, lists, inline emphasis) with a math-text cleanup
rule. Anything unrecognised falls through to a plain paragraph; rendering
never raises on malformed input.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable

logger = logging.getLogger(__name__)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
_NUMBER_RE = re.compile(r"^\s*\d+[.)]\s+(.*)$")

_INLINE_RE = re.compile(
    r"(?P<code>`[^`]*`)"
    r"|(?P<bold>\*\*.+?\*\*|__.+?__)"
    r"|(?P<math>\$[^$]+\$)"
    r"|(?P<italic>\*[^*]+?\*|_[^_]+?_)"
)

_MAX_TABLE_COLUMNS = 12


def clean_math_text(raw: str) -> str:
    """Clean LaTeX source per S-1 step 7 into legible plain text."""
    text = raw.strip()
    if text.startswith("$$") and text.endswith("$$") and len(text) >= 4:
        text = text[2:-2]
    elif text.startswith("$") and text.endswith("$") and len(text) >= 2:
        text = text[1:-1]
    for src, dst in (
        ("\\left", ""),
        ("\\right", ""),
        ("\\times", "×"),
        ("\\sum", "Σ"),
        ("\\ge", "≥"),
        ("\\le", "≤"),
        ("\\neq", "≠"),
        ("\\alpha", "α"),
        ("\\beta", "β"),
        ("\\Delta", "Δ"),
    ):
        text = text.replace(src, dst)
    text = re.sub(r"_\{([^}]*)\}", r"_\1", text)
    text = re.sub(r"\^\{([^}]*)\}", r"^\1", text)
    text = re.sub(r"\\([A-Za-z]+)", r"\1", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _split_inline_runs(line: str) -> list[tuple[str, str]]:
    """Split one line into ``(style, text)`` runs; style is plain/bold/italic/code."""
    out: list[tuple[str, str]] = []
    pos = 0
    for m in _INLINE_RE.finditer(line):
        if m.start() > pos:
            out.append(("plain", line[pos : m.start()]))
        kind = m.lastgroup or "plain"
        token = m.group()
        if kind == "code":
            out.append(("code", token[1:-1]))
        elif kind == "bold":
            out.append(("bold", token[2:-2]))
        elif kind == "math":
            out.append(("italic", clean_math_text(token)))
        else:
            out.append(("italic", token[1:-1]))
        pos = m.end()
    rest = line[pos:]
    if rest:
        opener = re.search(r"(?<!\*)\*(?!\*)|(?<!_)_(?!_)", rest)
        if opener and opener.end() < len(rest) and not rest[opener.end()].isspace():
            out.append(("plain", rest[: opener.start()]))
            out.append(("italic", rest[opener.end() :]))
        else:
            out.append(("plain", rest))
    return [(style, txt) for style, txt in out if txt]


def parse_pipe_table(lines: list[str]) -> list[list[str]] | None:
    """Return the normalised rectangular cell grid, or None when not a table."""
    if len(lines) < 2:
        return None
    align = lines[1].strip()
    if not align or set(align) - set("|-: ") or "-" not in align:
        return None

    def split_row(line: str) -> list[str]:
        s = line.strip()
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        return [cell.strip() for cell in s.split("|")]

    rows = [split_row(line) for line in lines]
    width = max(1, len(rows[0]))
    normalised: list[list[str]] = []
    for idx, row in enumerate(rows):
        if idx == 1:
            continue
        row = row[:width]
        row = row + [""] * (width - len(row))
        normalised.append(row)
    return normalised


def _strip_inline(line: str) -> str:
    return "".join(txt for _, txt in _split_inline_runs(line))


def _apply_runs(paragraph: Any, line: str) -> None:
    Pt = _pt()
    for style, txt in _split_inline_runs(line):
        run = paragraph.add_run(txt)
        if style == "bold":
            run.bold = True
        elif style == "italic":
            run.italic = True
        elif style == "code":
            run.font.name = "Consolas"
            run.font.size = Pt(9)


def _pt() -> Any:
    import importlib

    return getattr(importlib.import_module("docx.shared"), "Pt")


def render_markdown_body(
    doc: Any, text: str, on_display_math: Callable[[str], None] | None = None
) -> None:
    """Render ``text`` into ``doc`` following S-1; never raises."""
    try:
        _render_blocks(doc, text, on_display_math)
    except Exception:
        logger.warning("markdown_render_fallback", exc_info=True)
        try:
            for piece in text.split("\n"):
                if piece.strip():
                    doc.add_paragraph(piece.strip())
        except Exception:
            logger.warning("markdown_render_fallback_failed", exc_info=True)


def _render_blocks(doc: Any, text: str, on_display_math: Callable[[str], None] | None) -> None:
    WD_ALIGN_PARAGRAPH = _docx_enum_align()
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            i += 1
            continue

        if stripped.startswith("```"):
            i += 1
            inner: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                inner.append(lines[i])
                i += 1
            i += 1
            paragraph = doc.add_paragraph()
            run = paragraph.add_run("\n".join(inner))
            run.font.name = "Consolas"
            run.font.size = _pt()(9)
            continue

        heading = _HEADING_RE.match(raw)
        if heading:
            level = min(len(heading.group(1)) + 2, 4)
            try:
                doc.add_heading(heading.group(2).strip(), level=level)
            except Exception:
                paragraph = doc.add_paragraph(heading.group(2).strip())
                paragraph.runs[0].bold = True
            i += 1
            continue

        display_body: str | None = None
        if stripped == "$$":
            i += 1
            body_lines: list[str] = []
            while i < len(lines) and lines[i].strip() != "$$":
                body_lines.append(lines[i])
                i += 1
            i += 1
            display_body = "\n".join(body_lines)
        elif stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 4:
            display_body = stripped[2:-2]
            i += 1

        if display_body is not None:
            if on_display_math is not None:
                on_display_math(display_body)
            paragraph = doc.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run(clean_math_text(display_body))
            run.italic = True
            continue

        if stripped.startswith("|"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            block = lines[i:j]
            grid = parse_pipe_table(block)
            if grid is None:
                for line in block:
                    if line.strip():
                        _add_plain_paragraph(doc, line.strip())
            elif len(grid[0]) > _MAX_TABLE_COLUMNS:
                doc.add_paragraph(f"[Table with {len(grid[0])} columns rendered as text]")
                for line in block:
                    if line.strip():
                        _add_plain_paragraph(doc, line.strip())
            else:
                from pdd_agent.export.table_helpers import add_styled_table

                add_styled_table(doc, grid, widths=None, header=True, font_size=8.7)
            i = j
            continue

        bullet = _BULLET_RE.match(raw)
        numbered = _NUMBER_RE.match(raw)
        if bullet or numbered:
            content = (bullet or numbered).group(1)
            paragraph = doc.add_paragraph()
            _apply_style_safe(paragraph, "List Bullet" if bullet else "List Number")
            _apply_runs(paragraph, content)
            i += 1
            continue

        _add_plain_paragraph(doc, stripped)
        i += 1


def _add_plain_paragraph(doc: Any, line: str) -> None:
    paragraph = doc.add_paragraph()
    _apply_runs(paragraph, line)


def _apply_style_safe(paragraph: Any, style_name: str) -> None:
    try:
        paragraph.style = style_name
    except Exception:
        pass


def _docx_enum_align() -> Any:
    import importlib

    return getattr(importlib.import_module("docx.enum.text"), "WD_ALIGN_PARAGRAPH").CENTER
