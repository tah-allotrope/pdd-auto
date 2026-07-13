"""Tests for PDF export via LibreOffice CLI."""

import pytest
from unittest.mock import patch, MagicMock

from pdd_agent.export.pdf_export import (
    export_docx_to_pdf,
    is_libreoffice_available,
    PDFExportError,
)


class TestIsLibreOfficeAvailable:
    @patch("pdd_agent.export.pdf_export.shutil.which", return_value="/usr/bin/libreoffice")
    def test_available(self, _mock):
        assert is_libreoffice_available() is True

    @patch("pdd_agent.export.pdf_export.shutil.which", return_value=None)
    def test_not_available(self, _mock):
        assert is_libreoffice_available() is False


class TestExportDocxToPdf:
    def test_missing_docx_raises(self, tmp_path):
        fake_docx = tmp_path / "nonexistent.docx"
        with pytest.raises(PDFExportError, match="not found"):
            export_docx_to_pdf(fake_docx)

    @patch("pdd_agent.export.pdf_export._find_libreoffice", return_value=None)
    def test_no_libreoffice_raises(self, _mock, tmp_path):
        docx = tmp_path / "test.docx"
        docx.write_text("dummy")
        with pytest.raises(PDFExportError, match="LibreOffice not found"):
            export_docx_to_pdf(docx)

    @patch("pdd_agent.export.pdf_export.subprocess.run")
    @patch("pdd_agent.export.pdf_export._find_libreoffice", return_value="/usr/bin/libreoffice")
    def test_successful_conversion(self, _mock_lo, mock_run, tmp_path):
        docx = tmp_path / "test.docx"
        docx.write_text("dummy")
        pdf = tmp_path / "test.pdf"
        pdf.write_text("pdf content")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = export_docx_to_pdf(docx, output_dir=tmp_path)
        assert result == pdf
        mock_run.assert_called_once()

    @patch("pdd_agent.export.pdf_export.subprocess.run")
    @patch("pdd_agent.export.pdf_export._find_libreoffice", return_value="/usr/bin/libreoffice")
    def test_conversion_failure(self, _mock_lo, mock_run, tmp_path):
        docx = tmp_path / "test.docx"
        docx.write_text("dummy")

        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error occurred")

        with pytest.raises(PDFExportError, match="failed"):
            export_docx_to_pdf(docx, output_dir=tmp_path)

    @patch("pdd_agent.export.pdf_export.subprocess.run")
    @patch("pdd_agent.export.pdf_export._find_libreoffice", return_value="/usr/bin/libreoffice")
    def test_timeout(self, _mock_lo, mock_run, tmp_path):
        import subprocess

        docx = tmp_path / "test.docx"
        docx.write_text("dummy")

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="libreoffice", timeout=120)

        with pytest.raises(PDFExportError, match="timed out"):
            export_docx_to_pdf(docx, output_dir=tmp_path)

    @patch("pdd_agent.export.pdf_export.subprocess.run")
    @patch("pdd_agent.export.pdf_export._find_libreoffice", return_value="/usr/bin/libreoffice")
    def test_pdf_not_created(self, _mock_lo, mock_run, tmp_path):
        docx = tmp_path / "test.docx"
        docx.write_text("dummy")

        mock_run.return_value = MagicMock(returncode=0, stdout="Converted", stderr="")

        with pytest.raises(PDFExportError, match="not created"):
            export_docx_to_pdf(docx, output_dir=tmp_path)
