"""Document assembly: numbering and title-echo stripping (PHASE-05, S-3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdd_agent.export.assembly import (
    canonical_subsection_title,
    is_title_echo,
    strip_leading_title_heading,
)

_RUNS_DIR = Path(__file__).parent.parent / "data" / "runs"
_SMOKE_RUN = _RUNS_DIR / "smoke-4-1.json"


class TestCanonicalSubsectionTitle:
    def test_numbered_title(self):
        assert canonical_subsection_title("4.1", "Baseline Emissions") == "4.1 Baseline Emissions"

    def test_empty_id_returns_heading(self):
        assert canonical_subsection_title("", "Baseline Emissions") == "Baseline Emissions"


class TestIsTitleEcho:
    def test_numbered_echo_matches(self):
        assert is_title_echo("# 4.4.1 Baseline Emissions", "Baseline Emissions") is True

    def test_plain_heading_echo_matches(self):
        assert is_title_echo("## Baseline Emissions", "Baseline Emissions") is True

    def test_different_heading_does_not_match(self):
        assert is_title_echo("## Methodology Basis", "Baseline Emissions") is False


class TestStripLeadingTitleHeading:
    def test_echo_heading_removed(self):
        assert (
            strip_leading_title_heading(
                "# 4.4.1 Baseline Emissions\n\nUnder ACM0022...", "Baseline Emissions"
            )
            == "Under ACM0022..."
        )

    def test_non_echo_body_unchanged(self):
        body = "Under ACM0022..."
        assert strip_leading_title_heading(body, "Baseline Emissions") == body


@pytest.mark.skipif(not _SMOKE_RUN.exists(), reason="smoke-4-1 run file absent")
class TestSmokeExportHeadings:
    def test_numbered_heading_without_echo(self, tmp_path: Path):
        from docx import Document

        from pdd_agent.export.docx_export import export_run_to_docx

        out = export_run_to_docx("smoke-4-1", output_path=tmp_path / "smoke-4-1.docx", force=True)
        doc = Document(str(out))
        headings = [
            (p.style.name, p.text) for p in doc.paragraphs if p.style.name.startswith("Heading")
        ]
        assert ("Heading 2", "4.1 Baseline Emissions") in headings
        assert not any(text == "4.4.1 Baseline Emissions" for _, text in headings)
