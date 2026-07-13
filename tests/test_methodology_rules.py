"""Tests for MethodologyRules pre/post-draft compliance checks."""

from __future__ import annotations

from pdd_agent.domain.methodology_rules import get_methodology_rules


class TestRunPostDraftChecks:
    """POST-004 (rules/verra/wte_methodology_rules.yaml) has
    applies_to: ["ACM0022"] — it should only fire for ACM0022 projects.
    """

    def _rec_missing_sections(self) -> dict[str, str]:
        return {"1.16": "This project sells electricity to the grid."}

    def test_no_methodology_ids_runs_all_checks(self):
        """Backward compatibility: omitting methodology_ids runs every check,
        matching pre-fix behavior for existing callers."""
        rules = get_methodology_rules()
        failures = rules.run_post_draft_checks(self._rec_missing_sections())
        check_ids = {f["check_id"] for f in failures}
        assert "POST-004" in check_ids

    def test_acm0022_methodology_still_triggers_post_004(self):
        rules = get_methodology_rules()
        failures = rules.run_post_draft_checks(
            self._rec_missing_sections(), methodology_ids=["ACM0022"]
        )
        check_ids = {f["check_id"] for f in failures}
        assert "POST-004" in check_ids

    def test_non_acm0022_methodology_skips_post_004(self):
        """A rice VM0051 project should not be flagged by an ACM0022-only check."""
        rules = get_methodology_rules()
        failures = rules.run_post_draft_checks(
            self._rec_missing_sections(), methodology_ids=["VM0051"]
        )
        check_ids = {f["check_id"] for f in failures}
        assert "POST-004" not in check_ids

    def test_checks_without_applies_to_always_run(self):
        """POST-001..003 have no applies_to and must fire regardless of methodology."""
        rules = get_methodology_rules()
        sections = {"3.2": "The applicability conditions are described in detail below."}
        failures = rules.run_post_draft_checks(sections, methodology_ids=["VM0051"])
        check_ids = {f["check_id"] for f in failures}
        assert "POST-002" in check_ids
