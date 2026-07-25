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
