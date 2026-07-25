"""Tests for assistant-preamble normalization."""

from pdd_agent.llm.output_normalize import strip_assistant_preamble


class TestStripAssistantPreamble:
    def test_horizontal_rule_form(self):
        text = (
            "I'll draft a conservative summary paragraph for section 1.1.1 "
            "using the project-specific facts provided.\n\n"
            "---\n\n"
            "# 1.1.1 Summary Description of the Project\n\n"
            "The project is a facility."
        )
        result = strip_assistant_preamble(text)
        assert result == "# 1.1.1 Summary Description of the Project\n\nThe project is a facility."

    def test_leading_lines_form(self):
        result = strip_assistant_preamble(
            "Here's the section:\n\nThe project boundary includes the site."
        )
        assert result == "The project boundary includes the site."

    def test_no_preamble_unchanged(self):
        text = "The project boundary includes the site."
        assert strip_assistant_preamble(text) == text

    def test_heading_not_stripped(self):
        text = "# 1.1 Heading\n\nBody text."
        assert strip_assistant_preamble(text) == text

    def test_trailing_form(self):
        result = strip_assistant_preamble("Body text.\n\nLet me know if you'd like more detail.")
        assert result == "Body text."

    def test_would_empty_returns_original(self):
        text = "I'll draft this now."
        assert strip_assistant_preamble(text) == text

    def test_hr_without_preamble_preserved(self):
        text = "Baseline emissions are 1,000 tCO2e/year.\n\n---\n\nProject emissions are 200 tCO2e/year."
        assert strip_assistant_preamble(text) == text

    def test_empty_string(self):
        assert strip_assistant_preamble("") == ""

    def test_sure_prefix_stripped(self):
        text = "Sure, here's the section.\n\n# 3.3 Project Boundary\n\nThe boundary is defined."
        result = strip_assistant_preamble(text)
        assert result.startswith("# 3.3 Project Boundary")


class TestTrailerScanIsBounded:
    """A trailer phrase mid-body is real content, not conversational filler.

    "Note: I've assumed ..." is exactly how an assumption disclosure is worded
    in a PDD, so a trailer is only stripped when it forms an unbroken suffix of
    the body — a match with real content after it is not a trailer.
    """

    def test_mid_body_note_does_not_truncate(self):
        text = (
            "# 4.1 Baseline Emissions\n\n"
            "Baseline emissions are 49,680 tCO2e/year.\n\n"
            "Note: I've applied the national grid emission factor of 0.92 tCO2/MWh.\n\n"
            "# 4.2 Project Emissions\n\n"
            "Project emissions are 0 tCO2e/year."
        )
        result = strip_assistant_preamble(text)
        assert "# 4.2 Project Emissions" in result
        assert "Note: I've applied" in result

    def test_genuine_tail_trailer_still_removed(self):
        text = (
            "# 1.1 Summary\n\n"
            "The project diverts 262,970 tonnes/year.\n\n"
            "Let me know if you'd like more detail."
        )
        result = strip_assistant_preamble(text)
        assert result == "# 1.1 Summary\n\nThe project diverts 262,970 tonnes/year."

    def test_preamble_still_stripped_when_trailer_bounded(self):
        text = (
            "I'll draft a conservative summary paragraph for section 1.1.1.\n\n"
            "# 1.1.1 Summary Description\n\n"
            "The project is located in Bursa."
        )
        result = strip_assistant_preamble(text)
        assert result.startswith("# 1.1.1 Summary Description")

    def test_trailer_only_body_returns_original(self):
        text = "Let me know if you'd like more detail."
        assert strip_assistant_preamble(text) == text

    def test_multi_line_trailer_suffix_removed(self):
        text = "Body line one.\nBody line two.\nFeel free to ask.\nLet me know if you need more."
        result = strip_assistant_preamble(text)
        assert result == "Body line one.\nBody line two."

    def test_trailer_phrase_with_content_after_it_is_kept(self):
        text = (
            "Baseline is 1,000 tCO2e/year.\n\n"
            "Note: I've used the 2025 grid factor.\n\n"
            "Project emissions are 200 tCO2e/year."
        )
        result = strip_assistant_preamble(text)
        assert result == text
