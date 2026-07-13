"""CLI wiring tests for optional PDF export."""

from argparse import Namespace
from unittest.mock import MagicMock, patch

from pdd_agent.cli import _build_parser, _run_export
from pdd_agent.export.pdf_export import PDFExportError


def test_export_parser_accepts_pdf_flag():
    args = _build_parser().parse_args(["export", "--run-id", "run-1", "--pdf"])
    assert args.pdf is True


@patch("pdd_agent.cli.export_docx_to_pdf")
@patch("pdd_agent.cli.export_run_to_docx")
def test_export_converts_docx_and_reports_status(mock_docx, mock_pdf, tmp_path):
    docx = tmp_path / "run.docx"
    pdf = tmp_path / "run.pdf"
    mock_docx.return_value = docx
    mock_pdf.return_value = pdf
    log = MagicMock()

    _run_export(Namespace(run_id="run", output=None, review_output_dir=None, pdf=True), log)

    mock_pdf.assert_called_once_with(docx)
    log.info.assert_any_call(
        "export_complete",
        docx_path=str(docx),
        pdf_status="created",
        pdf_path=str(pdf),
    )


@patch("pdd_agent.cli.export_docx_to_pdf", side_effect=PDFExportError("LibreOffice not found"))
@patch("pdd_agent.cli.export_run_to_docx")
def test_export_skips_pdf_cleanly(mock_docx, _mock_pdf, tmp_path):
    mock_docx.return_value = tmp_path / "run.docx"
    log = MagicMock()
    _run_export(Namespace(run_id="run", output=None, review_output_dir=None, pdf=True), log)
    log.warning.assert_called_once_with("pdf_export_skipped", reason="LibreOffice not found")
