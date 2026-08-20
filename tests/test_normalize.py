"""Tests for normalization and text extraction."""

from __future__ import annotations

import sys
import types
from pathlib import Path

from pdd_agent.ingest.normalize import _extract_pdf, _extract_tables, _extract_text


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


class TestExtractTables:
    """PHASE-06 (2026-08-13 plan): pdfplumber table extraction, graceful degradation."""

    def test_without_pdfplumber_returns_empty_and_still_parseable(self, tmp_path, monkeypatch):
        # Simulate pdfplumber not installed by forcing ImportError on import.
        real_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "pdfplumber":
                raise ImportError("No module named pdfplumber")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", fake_import)
        # Reset warning flag so the warning is emitted and we can test the path.
        import pdd_agent.ingest.normalize as norm

        norm._pdfplumber_warning_emitted = False

        result = _extract_tables(Path("anything.pdf"))
        assert result == []

        # Normalization must still produce text and empty tables.
        fake_pdf = tmp_path / "test.pdf"
        # Create a minimal fake pdf file so _extract_text can attempt but pdfplumber path is mocked.
        result2 = _extract_text(fake_pdf, "application/pdf", dry_run=True)
        assert result2["tables"] == []
        assert result2["parseable"] is True

    def test_stub_extract_tables_with_none_cell(self, monkeypatch):
        stub_page = types.SimpleNamespace(extract_tables=lambda: [[["A", "B"], ["1", None]]])
        stub_pdf = types.SimpleNamespace(pages=[stub_page])
        stub_module = types.SimpleNamespace(open=lambda path: stub_pdf)
        stub_module.__enter__ = lambda self: stub_pdf
        stub_module.__exit__ = lambda *a: False
        # pdfplumber.open is a context manager; mock it properly.
        import contextlib

        @contextlib.contextmanager
        def fake_open(path):
            yield stub_pdf

        fake_plumber = types.SimpleNamespace(open=fake_open)
        monkeypatch.setitem(sys.modules, "pdfplumber", fake_plumber)
        import pdd_agent.ingest.normalize as norm

        norm._pdfplumber_warning_emitted = True
        result = _extract_tables(Path("dummy.pdf"))
        assert result == [{"page": 1, "table_index": 0, "rows": [["A", "B"], ["1", ""]]}]

    def test_extract_tables_handles_exception(self, monkeypatch):
        import contextlib

        stub_page = types.SimpleNamespace(
            extract_tables=lambda: (_ for _ in ()).throw(RuntimeError("boom"))
        )
        stub_pdf = types.SimpleNamespace(pages=[stub_page])

        @contextlib.contextmanager
        def fake_open(path):
            yield stub_pdf

        fake_plumber = types.SimpleNamespace(open=fake_open)
        monkeypatch.setitem(sys.modules, "pdfplumber", fake_plumber)
        import pdd_agent.ingest.normalize as norm

        norm._pdfplumber_warning_emitted = True
        result = _extract_tables(Path("dummy2.pdf"))
        # Should return whatever collected so far (empty) and not propagate.
        assert result == []

    def test_docx_tables_empty(self, tmp_path):
        from docx import Document

        docx_path = tmp_path / "test.docx"
        doc = Document()
        doc.add_paragraph("Hello world")
        doc.save(str(docx_path))
        result = _extract_text(
            docx_path,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            dry_run=False,
        )
        assert result["tables"] == []
