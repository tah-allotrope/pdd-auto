"""Document-level coherence checks (PHASE-05, Specification S-5)."""

from __future__ import annotations

from pdd_agent.review.document_coherence import check_document_coherence


def _section(sid: str, text: str) -> dict:
    section_id, _, sub = sid.partition(".")
    return {
        "section_id": section_id if sub else sid,
        "sub_section_id": sid if sub else "",
        "text": text,
    }


class TestNumberDisagreement:
    def test_flags_divergent_tco2e_numbers(self):
        run = {
            "sections": [
                _section("4.1", "Baseline displacement is 1,234,567 tCO2e per year."),
                _section("4.4", "Baseline displacement is 1,300,000 tCO2e per year."),
            ]
        }
        findings = check_document_coherence(run)
        number = [f for f in findings if f["check"] == "NUMBER_DISAGREEMENT"]
        assert len(number) == 1
        assert set(number[0]["sections"]) == {"4.1", "4.4"}


class TestDuplicateBody:
    def test_flags_identical_bodies(self):
        body = "This narrative body is identical in both sections word for word."
        run = {"sections": [_section("1.1", body), _section("1.2", body)]}
        findings = check_document_coherence(run)
        assert any(f["check"] == "DUPLICATE_BODY" for f in findings)


class TestDanglingCrossReference:
    def test_flags_unknown_section_reference(self):
        run = {
            "sections": [_section("1.1", "As described in Section 9.9, the plant exports power.")]
        }
        findings = check_document_coherence(run)
        assert any(f["check"] == "DANGLING_CROSS_REFERENCE" for f in findings)


class TestCleanRun:
    def test_no_issues_returns_empty(self):
        run = {"sections": [_section("1.1", "Plain narrative with no numbers or references.")]}
        assert check_document_coherence(run) == []
