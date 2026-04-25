"""Tests for review checks, consistency checks, and approval state model."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from pdd_agent.llm.provider import DraftRun, DraftSection
from pdd_agent.review.checks import (
    ReviewCheck,
    ReviewCheckResult,
    run_review_checks,
    summarize_review_result,
    _run_double_counting_guard,
    _run_quantitative_check,
)
from pdd_agent.review.consistency import (
    ConsistencyFlag,
    ConsistencyReport,
    check_quantitative_consistency,
    summarize_consistency_report,
)
from pdd_agent.review.states import (
    ReviewState,
    ReviewStateStore,
    SectionState,
    init_review_state,
)


def _make_draft(section_id, sub_section_id, text, confidence="HIGH", issues=None, provenance=None):
    return DraftSection(
        section_id=section_id,
        sub_section_id=sub_section_id,
        text=text or f"Drafted content for {section_id}.{sub_section_id}",
        confidence=confidence,
        provenance=provenance or [],
        issues=issues or [],
        provider="noop",
    )


def _make_run(sections=None, run_id="test-run-001"):
    run = DraftRun(run_id=run_id, project_name="Test WTE Project")
    for s in sections or []:
        run.add(s)
    return run


class TestReviewCheckResult:
    def test_passes_when_no_blocking_issues(self):
        result = ReviewCheckResult(run_id="r1", passed=True)
        assert result.passed is True

    def test_blocks_critical_severity(self):
        result = ReviewCheckResult(run_id="r1", passed=True)
        result.add_check(
            ReviewCheck(
                check_id="TEST-01",
                severity="CRITICAL",
                description="test",
                flag=True,
                message="Critical failure",
            )
        )
        assert result.passed is False
        assert len(result.blocking_issues) == 1


class TestRunDoubleCountingGuard:
    def test_dc01_fires_when_both_claims_no_allocation_in_1_16(self):
        guard_def = {
            "guard_id": "DC-01",
            "description": "Both landfill diversion and fuel substitution claimed",
            "trigger_condition": "both claims set",
            "blocking": True,
        }
        sections = {"1.16": "This project generates carbon credits."}
        from unittest.mock import MagicMock

        mock_input = MagicMock()
        mock_input.technology.landfill_diversion_claim = True
        mock_input.technology.fuel_substitution_claim = True

        check = _run_double_counting_guard(guard_def, mock_input, sections)
        assert check.flag is True
        assert "DC-01" in check.message
        assert check.severity == "CRITICAL"

    def test_dc01_passes_when_credit_allocation_mentioned(self):
        guard_def = {
            "guard_id": "DC-01",
            "description": "Both claims",
            "trigger_condition": "both claims set",
            "blocking": True,
        }
        sections = {
            "1.16": "Credit allocation table: 70% ACM0022 landfill diversion, 30% ACM0003 fuel substitution."
        }
        from unittest.mock import MagicMock

        mock_input = MagicMock()
        mock_input.technology.landfill_diversion_claim = True
        mock_input.technology.fuel_substitution_claim = True

        check = _run_double_counting_guard(guard_def, mock_input, sections)
        assert check.flag is False

    def test_dc02_fires_when_capacity_but_no_recs_mention(self):
        guard_def = {
            "guard_id": "DC-02",
            "description": "RECs not addressed",
            "trigger_condition": "capacity > 0",
            "blocking": True,
        }
        sections = {"1.15": "This project generates electricity from waste."}
        from unittest.mock import MagicMock

        mock_input = MagicMock()
        mock_input.technology.installed_capacity_mw = 25.0

        check = _run_double_counting_guard(guard_def, mock_input, sections)
        assert check.flag is True
        assert "DC-02" in check.message

    def test_dc02_passes_when_recs_mentioned(self):
        guard_def = {
            "guard_id": "DC-02",
            "description": "RECs not addressed",
            "trigger_condition": "capacity > 0",
            "blocking": True,
        }
        sections = {"1.15": "No RECs are being claimed for this project's electricity output."}
        from unittest.mock import MagicMock

        mock_input = MagicMock()
        mock_input.technology.installed_capacity_mw = 25.0

        check = _run_double_counting_guard(guard_def, mock_input, sections)
        assert check.flag is False


class TestRunQuantitativeCheck:
    def test_crediting_period_total_mismatch_flags(self):
        check_def = {
            "check": "crediting_period_total_consistency",
            "description": "Crediting period total mismatch",
            "severity": "HIGH",
            "tolerance": 0.01,
        }
        from unittest.mock import MagicMock

        mock_input = MagicMock()
        mock_input.quantification.net_emissions_tco2e_per_year = 50000.0
        mock_input.quantification.crediting_period_total_tco2e = 400000.0
        mock_input.dates.crediting_period_years = 10

        check = _run_quantitative_check(check_def, mock_input, {})
        assert check.flag is True
        assert "400" in check.message and "mismatch" in check.message.lower()

    def test_no_project_input_passes_without_flag(self):
        check_def = {
            "check": "section_1_10_matches_section_4_4",
            "description": "Net tCO2e mismatch",
            "severity": "CRITICAL",
            "tolerance": 0.01,
        }
        check = _run_quantitative_check(check_def, None, {})
        assert check.flag is True
        assert "ProjectInput not provided" in check.message


class TestConsistencyReport:
    def test_critical_flag_makes_passed_false(self):
        report = ConsistencyReport(run_id="r1")
        report.flags.append(
            ConsistencyFlag(
                section_a="1.10",
                section_b="4.4",
                field_name="net_tco2e",
                value_a=50000,
                value_b=45000,
                expected=None,
                tolerance=0.01,
                severity="CRITICAL",
                message="Mismatch",
            )
        )
        assert report.passed is False
        assert len(report.critical_flags) == 1


class TestCheckQuantitativeConsistency:
    def test_matching_net_values_passes(self):
        from unittest.mock import MagicMock

        mock_input = MagicMock()
        mock_input.quantification.net_emissions_tco2e_per_year = 50000.0
        mock_input.technology.annual_waste_throughput = 100000.0
        mock_input.technology.installed_capacity_mw = 25.0
        mock_input.quantification.crediting_period_total_tco2e = 500000.0
        mock_input.dates.crediting_period_years = 10

        sections = [
            _make_draft("1", "10", "Annual net: 50000 tCO2e/year", confidence="HIGH"),
            _make_draft("4", "4", "Net GHG reductions: 50000 tCO2e/year", confidence="HIGH"),
        ]
        report = check_quantitative_consistency(sections, mock_input, "run-1")
        assert report.passed is True

    def test_mismatched_net_values_flags_critical(self):
        from unittest.mock import MagicMock

        mock_input = MagicMock()
        mock_input.quantification.net_emissions_tco2e_per_year = 50000.0
        mock_input.technology.annual_waste_throughput = 100000.0
        mock_input.technology.installed_capacity_mw = 25.0
        mock_input.quantification.crediting_period_total_tco2e = 500000.0
        mock_input.dates.crediting_period_years = 10

        sections = [
            _make_draft("1", "10", "Annual net: 50000 tCO2e/year", confidence="HIGH"),
            _make_draft("4", "4", "Net: 45000 tCO2e/year", confidence="HIGH"),
        ]
        report = check_quantitative_consistency(sections, mock_input, "run-1")
        assert report.passed is False
        assert len(report.critical_flags) == 2


class TestReviewStateStore:
    def test_init_review_state_creates_all_sections(self):
        section_ids = [("1", "1"), ("1", "2"), ("3", "4")]
        store = init_review_state("run-x", "Test Project", section_ids)
        assert len(store.sections) == 3
        assert store.run_id == "run-x"
        assert store.project_name == "Test Project"

    def test_valid_transition_drafted_to_needs_domain_review(self):
        store = init_review_state("run-x", "Test", [("3", "5")])
        key = "3/5"
        ok, msg = store.set_state("3", "5", ReviewState.NEEDS_DOMAIN_REVIEW)
        assert ok is True
        assert store.sections[key].state == ReviewState.NEEDS_DOMAIN_REVIEW

    def test_invalid_transition_drafted_to_approved_blocked(self):
        store = init_review_state("run-x", "Test", [("1", "1")])
        ok, msg = store.set_state("1", "1", ReviewState.APPROVED)
        assert ok is False
        assert "Invalid transition" in msg

    def test_needs_input_can_revert_to_drafted(self):
        store = init_review_state("run-x", "Test", [("2", "1")])
        store.set_state("2", "1", ReviewState.NEEDS_INPUT)
        ok, _ = store.set_state("2", "1", ReviewState.DRAFTED)
        assert ok is True
        assert store.sections["2/1"].state == ReviewState.DRAFTED

    def test_all_approved_true_when_everything_approved(self):
        store = init_review_state("run-x", "Test", [("1", "1"), ("1", "2")])
        store.set_state("1", "1", ReviewState.READY_FOR_HUMAN_EDIT)
        store.set_state("1", "1", ReviewState.APPROVED)
        store.set_state("1", "2", ReviewState.READY_FOR_HUMAN_EDIT)
        store.set_state("1", "2", ReviewState.APPROVED)
        assert store.is_all_approved() is True

    def test_save_and_load_round_trip(self):
        store = init_review_state("run-roundtrip", "Test Project", [("1", "1"), ("3", "5")])
        store.set_state("1", "1", ReviewState.READY_FOR_HUMAN_EDIT)
        store.set_state("1", "1", ReviewState.APPROVED)
        store.set_state("3", "5", ReviewState.NEEDS_DOMAIN_REVIEW)
        with tempfile.TemporaryDirectory() as tmpdir:
            saved_path = store.save(output_dir=Path(tmpdir))
            loaded = ReviewStateStore.load("run-roundtrip", output_dir=Path(tmpdir))
            assert loaded.run_id == "run-roundtrip"
            assert loaded.sections["1/1"].state == ReviewState.APPROVED
            assert loaded.sections["3/5"].state == ReviewState.NEEDS_DOMAIN_REVIEW

    def test_add_note(self):
        store = init_review_state("run-notes", "Test", [("3", "4")])
        store.add_note("3", "4", "Baseline scenario needs site visit evidence", "expert_a")
        assert len(store.sections["3/4"].reviewer_notes) == 1
        assert "expert_a" in store.sections["3/4"].updated_by


class TestSummarizeReviewResult:
    def test_summarize_returns_correct_keys(self):
        result = ReviewCheckResult(run_id="r1", passed=True)
        result.blocking_issues.append("[TEST-01] Something failed")
        summary = summarize_review_result(result)
        assert "run_id" in summary
        assert "passed" in summary
        assert "blocking_issues" in summary
        assert summary["run_id"] == "r1"


class TestAssumptionAwareReviewChecks:
    def test_blocked_synthetic_inputs_flag_sensitive_sections(self):
        run = _make_run(
            [
                DraftSection(
                    section_id="4",
                    sub_section_id="4.1",
                    text="Baseline emissions placeholder.",
                    confidence="LOW",
                    provenance=[],
                    issues=[],
                    provider="noop",
                    synthetic_uses=[
                        {
                            "field_path": "quantification.baseline_emissions_tco2e_per_year",
                            "blocked_review": True,
                        }
                    ],
                    review_sensitivity="HIGH",
                    content_class="QUANTITATIVE",
                )
            ],
            run_id="assumption-run",
        )

        result = run_review_checks(run, project_input=None, run_id="assumption-run")

        assert any("review-gated synthetic inputs" in warning for warning in result.warnings)

    def test_critical_synthetic_dependency_creates_blocking_issue(self):
        run = _make_run(
            [
                DraftSection(
                    section_id="3",
                    sub_section_id="3.5",
                    text="Additionality placeholder.",
                    confidence="UNSUPPORTED",
                    provenance=[],
                    issues=[],
                    provider="noop",
                    synthetic_uses=[
                        {
                            "field_path": "quantification.project_emissions_tco2e_per_year",
                            "blocked_review": True,
                        }
                    ],
                    review_sensitivity="CRITICAL",
                    content_class="METHODOLOGY_DEPENDENT",
                )
            ],
            run_id="critical-assumption-run",
        )

        result = run_review_checks(run, project_input=None, run_id="critical-assumption-run")

        assert result.passed is False
        assert any(
            "Section 3.3.5 depends on review-gated synthetic inputs" in item
            for item in result.blocking_issues
        )


class TestSummarizeConsistencyReport:
    def test_summarize_returns_critical_flags(self):
        report = ConsistencyReport(run_id="r2")
        report.flags.append(
            ConsistencyFlag(
                section_a="1.10",
                section_b="4.4",
                field_name="net",
                value_a=50000,
                value_b=45000,
                expected=None,
                tolerance=0.01,
                severity="CRITICAL",
                message="Net values differ",
            )
        )
        summary = summarize_consistency_report(report)
        assert summary["critical_count"] == 1
        assert summary["passed"] is False
