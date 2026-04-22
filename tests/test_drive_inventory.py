"""Tests for the Drive inventory and manifest generation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from pdd_agent.ingest.drive import (
    _build_entry,
    _local_path_for,
    drive_inventory,
    is_blob,
    is_workspace_native,
)


class TestMimeClassification:
    def test_pdf_is_blob(self):
        assert is_blob("application/pdf") is True

    def test_docx_is_blob(self):
        assert (
            is_blob("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            is True
        )

    def test_google_doc_is_not_blob(self):
        assert is_blob("application/vnd.google-apps.document") is False

    def test_google_doc_is_workspace_native(self):
        assert is_workspace_native("application/vnd.google-apps.document") is True

    def test_folder_is_not_blob(self):
        assert is_blob("application/vnd.google-apps.folder") is False


class TestLocalPathDerivation:
    def test_safe_name_strips_spaces(self):
        p = _local_path_for("VCS Soc Son_Project-Description.pdf", "application/pdf")
        assert " " not in p.name

    def test_pdf_gets_pdf_extension(self):
        p = _local_path_for("my file", "application/pdf")
        assert p.suffix == ".pdf"

    def test_google_doc_gets_pdf_extension(self):
        p = _local_path_for("my doc", "application/vnd.google-apps.document")
        assert p.suffix == ".pdf"


class TestBuildEntry:
    def test_minimal_entry_has_required_fields(self):
        raw = {
            "id": "abc123",
            "name": "VCS_Test_Project-Description.pdf",
            "mimeType": "application/pdf",
            "modifiedTime": "2026-03-15T12:00:00Z",
            "parents": ["folder-id"],
            "size": "4096",
        }
        entry = _build_entry(raw)

        assert entry["id"] == "abc123"
        assert entry["bucket"] is None  # assigned later by bucket_documents
        assert entry["parseable"] is True
        assert entry["needs_export"] is False
        assert entry["local_raw_path"] is not None
        assert entry["inventory_uuid"] is not None
        assert "ingested_at" in entry

    def test_google_doc_flags_correctly(self):
        raw = {
            "id": "xyz789",
            "name": "Draft Notes",
            "mimeType": "application/vnd.google-apps.document",
            "modifiedTime": "2026-04-01T00:00:00Z",
            "parents": [],
            "size": "0",
        }
        entry = _build_entry(raw)
        assert entry["parseable"] is False
        assert entry["needs_export"] is True


class TestDriveInventory:
    @patch("subprocess.run")
    def test_inventory_writes_manifest(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "files": [
                        {
                            "id": "file1",
                            "name": "VCS_Test.pdf",
                            "mimeType": "application/pdf",
                            "modifiedTime": "2026-01-01T00:00:00Z",
                            "parents": ["folder1"],
                            "size": "1024",
                        },
                        {
                            "id": "file2",
                            "name": "VCS_WTE.pdf",
                            "mimeType": "application/pdf",
                            "modifiedTime": "2026-01-02T00:00:00Z",
                            "parents": ["folder1"],
                            "size": "2048",
                        },
                    ]
                }
            ),
            stderr="",
        )

        manifest_path = str(tmp_path / "manifest.jsonl")
        entries = drive_inventory("folder1", manifest_path, dry_run=False)

        assert len(entries) == 2
        assert Path(manifest_path).exists()
        with open(manifest_path) as fh:
            lines = fh.readlines()
        assert len(lines) == 2
        first_entry = json.loads(lines[0])
        assert first_entry["id"] == "file1"

    @patch("subprocess.run")
    def test_dry_run_does_not_write(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"files": []}),
            stderr="",
        )
        manifest_path = str(tmp_path / "manifest.jsonl")
        entries = drive_inventory("folder1", manifest_path, dry_run=True)
        assert Path(manifest_path).exists() is False
        assert entries == []
