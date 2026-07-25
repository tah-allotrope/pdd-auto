"""Strip assistant preamble and trailer from real-provider output.

Real LLM providers sometimes wrap their answer in conversational filler
("I'll draft a conservative summary...", "Let me know if you'd like more
detail."). This module removes that filler so exported section bodies
start at the content and end at the content.
"""

from __future__ import annotations

import re

_PREAMBLE_RE = re.compile(
    r"^(i'?ll |i will |i'?m going to |let me |here'?s |here is "
    r"|sure[,.! ]|certainly[,.! ]|of course[,.! ]|i'?ve drafted |below is )",
    re.IGNORECASE,
)

_TRAILER_RE = re.compile(
    r"^(let me know|would you like|i hope this helps|feel free to"
    r"|note: i'?ve |shall i )",
    re.IGNORECASE,
)

_HORIZONTAL_RULES = {"---", "***", "___"}

# A trailer phrase is only conversational filler when it forms an unbroken suffix
# of the body. Mid-document, "Note: I've assumed ..." is how a PDD discloses an
# assumption, so matching anywhere would silently delete real content that
# follows it.


def strip_assistant_preamble(text: str) -> str:
    """Remove leading conversational preamble and trailing conversational tail."""
    if not text or not text.strip():
        return text

    lines = text.split("\n")

    non_empty_stripped = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            cleaned = stripped.lstrip("*_")
            non_empty_stripped.append((stripped, cleaned))

    hr_index = None
    for i, (stripped, _cleaned) in enumerate(non_empty_stripped[:5]):
        if stripped in _HORIZONTAL_RULES:
            preceding_preamble = any(_PREAMBLE_RE.match(c) for _, c in non_empty_stripped[:i])
            if preceding_preamble:
                hr_line = stripped
                for idx, line in enumerate(lines):
                    if line.strip() == hr_line:
                        hr_index = idx
                        break
                break

    if hr_index is not None:
        lines = lines[hr_index + 1 :]
    else:
        drop_count = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            cleaned = stripped.lstrip("*_")
            if stripped.startswith("#") or not _PREAMBLE_RE.match(cleaned):
                break
            drop_count = i + 1
        if drop_count > 0:
            lines = lines[drop_count:]

    # Walk backwards over non-empty lines while they look conversational; the cut
    # point is the first line of that suffix block. A trailer phrase with real
    # content after it is not a trailer.
    non_empty_indices = [i for i, line in enumerate(lines) if line.strip()]
    trailer_start = None
    for i in reversed(non_empty_indices):
        cleaned = lines[i].strip().lstrip("*_")
        if not _TRAILER_RE.match(cleaned):
            break
        trailer_start = i
    if trailer_start is not None:
        lines = lines[:trailer_start]

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    result = "\n".join(lines)
    if not result.strip():
        return text
    return result
