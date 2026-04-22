"""Tests for corpus bucket assignment."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from pdd_agent.ingest.bucket import _score_entry, load_bucket_config


class TestScoreEntry:
    def get_minimal_entry(self, name="VCS_Test_Project-Description.pdf"):
        return {
            "id": "abc123",
            "name": name,
            "mime_type": "application/pdf",
            "word_count": 5000,
            "heading_count": 50,
        }

    def test_wte_name_scored_in_bucket(self):
        entry = self.get_minimal_entry("VCS_Soc Son_Waste_to_Power_Project-Description.pdf")
        label, reason = _score_entry(entry, {"name_patterns": [r"vcs_.*soc.*son"]}, {})
        assert label == "IN_BUCKET"

    def test_draft_internal_excluded(self):
        entry = self.get_minimal_entry("Draft_Internal_Notes.pdf")
        label, reason = _score_entry(
            entry,
            {"name_patterns": [r"vcs_.*"]},
            {"name_patterns": [r"draft.*internal"]},
        )
        assert label == "OUT_OF_BUCKET"
        assert "exclusion" in reason.lower()

    def test_low_word_count_flagged(self):
        entry = self.get_minimal_entry("VCS_Test.pdf")
        entry["word_count"] = 50
        label, reason = _score_entry(entry, {"name_patterns": [r"vcs_.*"]}, {})
        assert label == "NEEDS_REVIEW"
        assert "word" in reason.lower()

    def test_google_doc_not_blob_excluded(self):
        entry = self.get_minimal_entry("My Doc.pdf")
        entry["mime_type"] = "application/vnd.google-apps.document"
        entry["word_count"] = 0
        label, reason = _score_entry(entry, {"name_patterns": [r".*"]}, {})
        assert label == "OUT_OF_BUCKET"


class TestLoadBucketConfig:
    def test_load_returns_dict(self):
        config = load_bucket_config()
        assert isinstance(config, dict)
