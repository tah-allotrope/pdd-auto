"""Tests for normalization and text extraction."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from pdd_agent.ingest.normalize import _extract_pdf, _extract_text, NORM_DIR


class TestExtractPdf:
    def test_dry_run_returns_placeholder(self, tmp_path):
        fake_pdf = tmp_path / "test.pdf"
        result = _extract_pdf(fake_pdf, dry_run=True)
        assert result["parseable"] is True
        assert "[dry-run" in result["text"]

    def test_missing_file_returns_error(self, tmp_path):
        fake_pdf = tmp_path / "nonexistent.pdf"
        result = _extract_pdf(fake_pdf, dry_run=False)
        assert result["parseable"] is False
        assert "error" in result


class TestExtractText:
    def test_pdf_flow(self, tmp_path):
        fake_pdf = tmp_path / "test.pdf"
        result = _extract_text(fake_pdf, "application/pdf", dry_run=True)
        assert result["parseable"] is True
        assert "word_count" in result
        assert "heading_count" in result

    def test_unknown_mime_returns_error(self, tmp_path):
        fake_bin = tmp_path / "file.bin"
        result = _extract_text(fake_bin, "application/octet-stream", dry_run=False)
        assert result["parseable"] is False
        assert "error" in result
