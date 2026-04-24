"""CLI entry-point for pdd-agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import structlog
import yaml

from pdd_agent.ingest.drive import drive_inventory
from pdd_agent.ingest.normalize import normalize_corpus
from pdd_agent.ingest.bucket import load_bucket_config, bucket_documents
from pdd_agent.ingest.download import download_corpus
from pdd_agent.retrieval.index import RetrievalIndex
from pdd_agent.agent.section_orchestrator import SectionOrchestrator
from pdd_agent.export.docx_export import export_run_to_docx
from pdd_agent.export.drive_upload import upload_file, upload_docx_run
from pdd_agent.phase05.benchmark import create_demo_project_input, run_demo_benchmark
from schemas.project_input import ProjectInput


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdd-agent",
        description="Agentic low-cost WTE carbon-credit PDD drafting tool",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("inventory", help="Inventory Drive folder and write manifest")
    sub.add_parser("download", help="Download corpus files from Drive manifest")
    sub.add_parser("normalize", help="Normalize raw corpus files to plain text")
    sub.add_parser("bucket", help="Assign corpus documents to homogeneity buckets")
    sub.add_parser(
        "ingest", help="Run full ingestion pipeline (inventory → download → normalize → bucket)"
    )

    build_idx = sub.add_parser(
        "build-index", help="Build the FTS5 retrieval index from normalized corpus"
    )
    build_idx.add_argument(
        "--corpus-dir",
        default="data/corpus/normalized",
        help="Normalized corpus directory",
    )
    build_idx.add_argument(
        "--index-db",
        default="data/index/corpus.fts.db",
        help="Output FTS5 database path",
    )

    draft_parser = sub.add_parser("draft", help="Draft all PDD sections for a project")
    draft_parser.add_argument("--input", "-i", required=True, help="Path to ProjectInput YAML file")
    draft_parser.add_argument(
        "--run-id", help="Optional run identifier (auto-generated if not provided)"
    )
    draft_parser.add_argument(
        "--provider",
        default="noop",
        help="LLM provider name (default: noop)",
    )

    review_parser = sub.add_parser("review", help="Run review checks on a draft run")
    review_parser.add_argument("--run-id", required=True, help="Run identifier to review")
    review_parser.add_argument(
        "--input", help="Path to ProjectInput YAML (for cross-reference checks)"
    )

    export_parser = sub.add_parser("export", help="Export a draft run to DOCX")
    export_parser.add_argument("--run-id", required=True, help="Run identifier to export")
    export_parser.add_argument(
        "--output", "-o", help="Output DOCX path (default: data/runs/{run_id}.docx)"
    )

    upload_parser = sub.add_parser("upload", help="Upload a DOCX to Google Drive")
    upload_parser.add_argument(
        "--run-id", required=True, help="Run identifier to upload (will upload {run-id}.docx)"
    )
    upload_parser.add_argument(
        "--folder-id",
        default="1pp23yRZ8qtopw1BPXrzVewXsmmWplCse",
        help="Target Drive folder ID",
    )

    demo_config_parser = sub.add_parser(
        "demo-config", help="Write the reproducible Soc Son-like demo ProjectInput"
    )
    demo_config_parser.add_argument(
        "--output",
        default="configs/projects/demo_socson_like.yaml",
        help="Output YAML path",
    )

    benchmark_parser = sub.add_parser(
        "benchmark", help="Run the Phase 05 demo benchmark and generate scorecards"
    )
    benchmark_parser.add_argument(
        "--input",
        default="configs/projects/demo_socson_like.yaml",
        help="Path to demo ProjectInput YAML",
    )
    benchmark_parser.add_argument(
        "--reference",
        help="Optional normalized Soc Son reference path (.norm.json)",
    )
    benchmark_parser.add_argument(
        "--existing-run",
        help="Optional path to an existing run JSON to benchmark without re-drafting",
    )
    benchmark_parser.add_argument(
        "--reports-dir",
        default="reports",
        help="Directory for demo-scorecard.md and section-diff.md",
    )
    benchmark_parser.add_argument(
        "--no-export",
        action="store_true",
        help="Skip DOCX export during benchmark",
    )

    parser.add_argument(
        "--folder-id",
        default="1pp23yRZ8qtopw1BPXrzVewXsmmWplCse",
        help="Google Drive folder ID to ingest (default: VERRA shared folder)",
    )
    parser.add_argument(
        "--manifest",
        default="data/corpus/manifest.jsonl",
        help="Path for manifest output",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without making changes",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(-30 if args.verbose else 20),
    )
    log = structlog.get_logger()

    commands: dict = {
        "inventory": lambda: drive_inventory(args.folder_id, args.manifest, args.dry_run),
        "download": lambda: download_corpus(args.manifest, args.dry_run),
        "normalize": lambda: normalize_corpus(args.manifest, args.dry_run),
        "bucket": lambda: _run_bucket(args.manifest),
        "ingest": lambda: _run_ingest(args.folder_id, args.manifest, args.dry_run, log),
        "build-index": lambda: _run_build_index(args, log),
        "draft": lambda: _run_draft(args, log),
        "review": lambda: _run_review(args, log),
        "export": lambda: _run_export(args, log),
        "upload": lambda: _run_upload(args, log),
        "demo-config": lambda: _run_demo_config(args, log),
        "benchmark": lambda: _run_benchmark(args, log),
    }

    try:
        commands[args.command]()
        return 0
    except Exception as exc:
        log.error("command_failed", command=args.command, error=str(exc))
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


def _run_bucket(manifest: str) -> None:
    cfg = load_bucket_config()
    bucket_documents(manifest, cfg)


def _run_ingest(folder_id: str, manifest: str, dry_run: bool, log) -> None:
    log.info("ingest_start", folder_id=folder_id)
    drive_inventory(folder_id, manifest, dry_run)
    download_corpus(manifest, dry_run)
    normalize_corpus(manifest, dry_run)
    cfg = load_bucket_config()
    bucket_documents(manifest, cfg)
    log.info("ingest_done")


def _run_build_index(args, log) -> None:
    log.info("build_index_start", corpus_dir=args.corpus_dir, db=args.index_db)
    idx = RetrievalIndex(db_path=args.index_db)
    idx.build(normalized_dir=Path(args.corpus_dir))
    log.info("build_index_done", db=args.index_db)


def _run_draft(args, log) -> None:
    input_path = Path(args.input)
    if not input_path.exists():
        log.error("input_file_not_found", path=str(input_path))
        return

    with open(input_path, encoding="utf-8") as f:
        input_data = yaml.safe_load(f)
    project_input = ProjectInput.model_validate(input_data)

    from pdd_agent.llm.provider import get_provider_registry, configure_provider, ModelConfig

    if args.provider != "noop":
        log.warning(
            "provider_not_fully_wired", provider=args.provider, note="Only noop is available"
        )
    provider = get_provider_registry().get(args.provider)

    orchestrator = SectionOrchestrator(
        provider=provider,
        project_input=project_input,
        run_id=args.run_id,
    )

    run = orchestrator.run()
    draft_path = run.save()
    log.info("draft_complete", run_id=orchestrator.run_id, saved=str(draft_path))

    review_out = orchestrator.run_review()
    log.info(
        "review_complete",
        run_id=orchestrator.run_id,
        passed=review_out["review"]["passed"],
        auto_approved=review_out["review"].get("auto_approved_sections", []),
        blocking=review_out["review"].get("blocking_issues", []),
    )


def _run_review(args, log) -> None:
    from pdd_agent.review.states import ReviewStateStore

    project_input = None
    if args.input:
        with open(args.input, encoding="utf-8") as f:
            project_input = ProjectInput.model_validate(yaml.safe_load(f))

    try:
        store = ReviewStateStore.load(args.run_id)
        log.info("review_state_loaded", run_id=args.run_id, state_count=len(store.sections))
        for key, sec in store.sections.items():
            log.info("section_state", key=key, state=sec.state.value)
    except FileNotFoundError:
        log.warning("no_review_state_found", run_id=args.run_id)


def _run_export(args, log) -> None:
    output_path = Path(args.output) if args.output else None
    result = export_run_to_docx(run_id=args.run_id, output_path=output_path)
    if result:
        log.info("docx_exported", path=str(result))
    else:
        log.error("docx_export_failed", run_id=args.run_id)


def _run_upload(args, log) -> None:
    log.info("upload_start", run_id=args.run_id, folder=args.folder_id)
    result = upload_docx_run(run_id=args.run_id, drive_folder_id=args.folder_id)
    if result["success"]:
        log.info("upload_success", drive_url=result["drive_url"])
    else:
        log.error("upload_failed", error=result["error"])


def _run_demo_config(args, log) -> None:
    path = create_demo_project_input(Path(args.output))
    log.info("demo_config_written", path=str(path))


def _run_benchmark(args, log) -> None:
    artifacts = run_demo_benchmark(
        project_input_path=Path(args.input),
        reference_norm_path=Path(args.reference) if args.reference else None,
        reports_dir=Path(args.reports_dir),
        existing_run_path=Path(args.existing_run) if args.existing_run else None,
        export_docx=not args.no_export,
    )
    log.info(
        "benchmark_complete",
        run_id=artifacts.run_id,
        scorecard=str(artifacts.demo_scorecard),
        diff=str(artifacts.section_diff),
        runtime_seconds=artifacts.runtime_seconds,
        matched_sections=artifacts.comparison_summary.get("matched_sections"),
    )


if __name__ == "__main__":
    sys.exit(main())
