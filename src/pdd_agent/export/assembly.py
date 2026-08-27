"""Assembly helpers for DOCX export: numbering and title-echo stripping."""

from __future__ import annotations

import re

_ATX_RE = re.compile(r"^\s*#{1,6}\s+")
_NUMERIC_PREFIX_RE = re.compile(r"^\d+(\.\d+)*\.?\s*")


def canonical_subsection_title(sub_section_id: str, heading: str) -> str:
    """Return '1.1 Heading' or just heading when sub_section_id is empty."""
    if sub_section_id:
        return f"{sub_section_id} {heading}"
    return heading


def _normalize_title(text: str) -> str:
    """Remove leading numeric label, lower-case, collapse whitespace."""
    t = text.strip()
    # remove ATX heading markers if present
    t = _ATX_RE.sub("", t).strip()
    t = _NUMERIC_PREFIX_RE.sub("", t).strip()
    t = re.sub(r"\s+", " ", t.lower()).strip()
    return t


def is_title_echo(line: str, heading: str) -> bool:
    """True when line is an ATX heading whose text matches heading after normalization."""
    if not _ATX_RE.match(line.lstrip()):
        return False
    return _normalize_title(line) == _normalize_title(heading)


def strip_leading_title_heading(text: str, heading: str) -> str:
    """Remove first non-blank ATX heading line when it echoes the canonical heading."""
    if not text:
        return text
    lines = text.splitlines()
    # find first non-blank
    idx = None
    for i, ln in enumerate(lines):
        if ln.strip():
            idx = i
            break
    if idx is None:
        return text
    if is_title_echo(lines[idx], heading):
        # remove that line, keep rest, collapse leading blanks
        remaining = lines[idx + 1 :]
        # strip leading blank lines
        while remaining and not remaining[0].strip():
            remaining.pop(0)
        # preserve any leading blanks before idx? No, just join remaining
        prefix = lines[:idx]  # blanks before
        # combine prefix blanks (if any) + remaining
        result_lines = prefix + remaining
        return "\n".join(result_lines).lstrip("\n")
    return text
