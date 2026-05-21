"""Tests for TBD tracker — placeholder detection and evidence mapping."""

import pytest
from pathlib import Path

from pdd_agent.review.tbd_tracker import TBDTracker, TBDReport, TBDItem
from pdd_agent.llm.provider import DraftSection


def _make_section(section_id: str, sub_section_id: str, text: str) -> DraftSection:
    return DraftSection(
        section_id=section_id,
        sub_section_id=sub_section_id,
        text=text,
        confidence="MEDIUM",
        provenance=[],
        issues=[],
        provider="noop",
    )


class TestTBDDetection:
    def test_detects_tbd_marker(self):
        tracker = TBDTracker()
        section = _make_section(
            section_id="1",
            sub_section_id="1.10",
            text="The net emission reduction is [TBD - awaiting validation].",
        )
        report = tracker.scan([section], run_id="test-run")
        assert report.count == 1
        assert report.items[0].marker == "[TBD - awaiting validation]"
        assert report.items[0].section_id == "1"

    def test_detects_placeholder_marker(self):
        tracker = TBDTracker()
        section = _make_section(
            section_id="3",
            sub_section_id="3.2",
            text="Applicability condition 1: [PLACEHOLDER].",
        )
        report = tracker.scan([section], run_id="test-run")
        assert report.count == 1
        assert "PLACEHOLDER" in report.items[0].marker

    def test_detects_insert_marker(self):
        tracker = TBDTracker()
        section = _make_section(
            section_id="4",
            sub_section_id="4.1",
            text="Baseline emissions: [INSERT calculation here].",
        )
        report = tracker.scan([section], run_id="test-run")
        assert report.count == 1
        assert "INSERT" in report.items[0].marker

    def test_detects_source_marker(self):
        tracker = TBDTracker()
        section = _make_section(
            section_id="5",
            sub_section_id="5.2",
            text="Grid emission factor: [SOURCE: national authority].",
        )
        report = tracker.scan([section], run_id="test-run")
        assert report.count == 1
        assert "SOURCE" in report.items[0].marker

    def test_detects_evidence_marker(self):
        tracker = TBDTracker()
        section = _make_section(
            section_id="2",
            sub_section_id="2.3",
            text="EIA reference: [EVIDENCE REQUIRED].",
        )
        report = tracker.scan([section], run_id="test-run")
        assert report.count == 1
        assert "EVIDENCE" in report.items[0].marker

    def test_case_insensitive(self):
        tracker = TBDTracker()
        section = _make_section(
            section_id="1",
            sub_section_id="1.1",
            text="[tbd] and [Placeholder] and [insert].",
        )
        report = tracker.scan([section], run_id="test-run")
        assert report.count == 3

    def test_multiple_markers_same_section(self):
        tracker = TBDTracker()
        section = _make_section(
            section_id="3",
            sub_section_id="3.3",
            text="""
Included sources: [TBD - list sources].
Excluded sources: [TBD - list exclusions].
Geographic boundary: [INSERT coordinates].
""",
        )
        report = tracker.scan([section], run_id="test-run")
        assert report.count == 3
        # All three should be in section 3.3
        assert all(item.sub_section_id == "3.3" for item in report.items)

    def test_no_false_positives_on_legitimate_brackets(self):
        tracker = TBDTracker()
        section = _make_section(
            section_id="1",
            sub_section_id="1.1",
            text="The project is located in [İnegöl, Bursa] and uses [ACM0022].",
        )
        report = tracker.scan([section], run_id="test-run")
        assert report.count == 0

    def test_empty_text(self):
        tracker = TBDTracker()
        section = _make_section(section_id="1", sub_section_id="1.1", text="")
        report = tracker.scan([section], run_id="test-run")
        assert report.count == 0

    def test_no_text_attribute(self):
        tracker = TBDTracker()
        class FakeSection:
            section_id = "1"
            sub_section_id = ""
        report = tracker.scan([FakeSection()], run_id="test-run")
        assert report.count == 0


class TestTBDEvidenceMapping:
    def test_evidence_type_from_schema(self):
        tracker = TBDTracker()
        section = _make_section(
            section_id="1",
            sub_section_id="1.10",
            text="Net emissions: [TBD].",
        )
        report = tracker.scan([section], run_id="test-run")
        assert report.count == 1
        item = report.items[0]
        # Section 1.10 evidence_required from schema:
        # - Annual waste throughput (tonnes/year)
        # - Installed capacity (MW)
        # - Estimated annual tCO2e reductions
        assert item.evidence_type is not None
        assert "Annual waste throughput" in item.evidence_type

    def test_no_evidence_for_unknown_section(self):
        tracker = TBDTracker()
        section = _make_section(
            section_id="99",
            sub_section_id="99.1",
            text="Something [TBD].",
        )
        report = tracker.scan([section], run_id="test-run")
        assert report.count == 1
        assert report.items[0].evidence_type is None


class TestTBDReport:
    def test_sections_with_tbd(self):
        report = TBDReport(run_id="test")
        report.items = [
            TBDItem("1", "1.10", "[TBD]", "text", 1),
            TBDItem("1", "1.10", "[TBD]", "text", 2),
            TBDItem("3", "3.3", "[INSERT]", "text", 1),
        ]
        assert report.sections_with_tbd == ["1.10", "3.3"]

    def test_to_dict(self):
        report = TBDReport(run_id="test")
        report.items = [
            TBDItem("1", "1.10", "[TBD]", "context", 1, "evidence"),
        ]
        d = report.to_dict()
        assert d["run_id"] == "test"
        assert d["count"] == 1
        assert d["sections_with_tbd"] == ["1.10"]
        assert d["items"][0]["marker"] == "[TBD]"
        assert d["items"][0]["evidence_type"] == "evidence"
