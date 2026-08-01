"""CLI entry-point for pdd-agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import structlog
import yaml
from dotenv import find_dotenv, load_dotenv

from pdd_agent.ingest.drive import drive_inventory
from pdd_agent.ingest.normalize import normalize_corpus
from pdd_agent.ingest.bucket import load_bucket_config, bucket_documents
from pdd_agent.ingest.download import download_corpus
from pdd_agent.retrieval.index import RetrievalIndex
from pdd_agent.agent.section_orchestrator import SectionOrchestrator
from pdd_agent.export.docx_export import export_run_to_docx
from pdd_agent.export.pdf_export import PDFExportError, export_docx_to_pdf
from pdd_agent.export.drive_upload import upload_docx_run, upload_review_package_docx
from pdd_agent.export.review_package import publish_docx_run_for_review
from pdd_agent.phase05.benchmark import create_demo_project_input, run_demo_benchmark
from pdd_agent.phase06.assumptions import load_assumption_register, resolve_assumptions_path
from pdd_agent.phase06.spreadsheet_mapper import fetch_workbook, generate_project_artifacts
from pdd_agent.phase06.vietnam_workflow import run_vietnam_pdd_workflow
from pdd_agent.doctor import run_doctor
from pdd_agent.llm.env_config import configure_provider_from_env
from schemas.project_input import ProjectInput

# Alias retained for any external callers; use configure_provider_from_env directly
# in new code.
_configure_api_provider = configure_provider_from_env


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

    sub.add_parser(
        "demo-setup",
        help="Build the demo FTS5 index from the bundled demo/corpus subset",
    )

    sub.add_parser(
        "doctor",
        help="Diagnose the local environment: Python version, optional packages, "
        "API keys, Ollama, external tools, retrieval index, model pricing",
    )

    draft_parser = sub.add_parser("draft", help="Draft all PDD sections for a project")
    draft_parser.add_argument("--input", "-i", required=True, help="Path to ProjectInput YAML file")
    draft_parser.add_argument(
        "--run-id", help="Optional run identifier (auto-generated if not provided)"
    )
    draft_parser.add_argument(
        "--provider",
        default="noop",
        help="Drafting provider name: noop, demo, corpus, openai, anthropic, ollama (default: noop)",
    )
    judge_group = draft_parser.add_mutually_exclusive_group()
    judge_group.add_argument(
        "--judge",
        action="store_true",
        default=False,
        help="Run the LLM judge and capped auto-redraft loop after each section (default: no-judge)",
    )
    judge_group.add_argument(
        "--no-judge",
        action="store_false",
        dest="judge",
        help="Explicitly disable the judge/redraft loop (default)",
    )

    review_parser = sub.add_parser("review", help="Run review checks on a draft run")
    review_parser.add_argument("--run-id", required=True, help="Run identifier to review")
    review_parser.add_argument(
        "--input", help="Path to ProjectInput YAML (for cross-reference checks)"
    )

    judge_parser = sub.add_parser("judge", help="Run the LLM judge on an existing draft run")
    judge_parser.add_argument("--run-id", required=True, help="Run identifier to judge")
    judge_parser.add_argument(
        "--input", help="Path to ProjectInput YAML (for evidence registry and calc cross-checks)"
    )

    export_parser = sub.add_parser("export", help="Export a draft run to DOCX")
    export_parser.add_argument("--run-id", required=True, help="Run identifier to export")
    export_parser.add_argument(
        "--output", "-o", help="Output DOCX path (default: data/runs/{run_id}.docx)"
    )
    export_parser.add_argument(
        "--input",
        help="ProjectInput YAML for export gate cross-checks (evidence registry, calc numbers)",
    )
    export_parser.add_argument(
        "--force",
        action="store_true",
        help="Override export gate hard-blocks and export a watermarked DRAFT",
    )
    export_parser.add_argument(
        "--review-output-dir",
        help="Optional reviewer-facing publication root for the exported DOCX",
    )
    export_parser.add_argument(
        "--pdf",
        action="store_true",
        help="Convert the exported DOCX to PDF when LibreOffice is available",
    )

    upload_parser = sub.add_parser("upload", help="Upload a DOCX to Google Drive")
    upload_target = upload_parser.add_mutually_exclusive_group(required=True)
    upload_target.add_argument(
        "--run-id", help="Run identifier to upload (will upload {run-id}.docx)"
    )
    upload_target.add_argument(
        "--review-docx",
        help="Path to a published reviewer-facing DOCX to upload",
    )
    upload_parser.add_argument(
        "--folder-id",
        default="1pp23yRZ8qtopw1BPXrzVewXsmmWplCse",
        help="Target Drive folder ID",
    )

    fetch_registry_parser = sub.add_parser(
        "fetch-registry", help="Download registered PDD PDFs from the public Verra registry"
    )
    fetch_registry_parser.add_argument(
        "--methodology", required=True, help="Methodology ID, e.g. VM0051, VM0044, AMS-II.G"
    )
    fetch_registry_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of PDDs to fetch (default: 10)"
    )
    fetch_registry_parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write downloaded PDFs and manifest.json into",
    )

    scorecard_parser = sub.add_parser(
        "scorecard", help="Run the same ProjectInput through multiple providers and compare"
    )
    scorecard_parser.add_argument(
        "--input", "-i", required=True, help="Path to ProjectInput YAML file"
    )
    scorecard_parser.add_argument(
        "--providers",
        default="demo",
        help="Comma-separated provider names, e.g. ollama,openai,anthropic (default: demo)",
    )
    scorecard_parser.add_argument(
        "--output",
        default="reports/provider-scorecard.md",
        help="Output markdown path (default: reports/provider-scorecard.md)",
    )
    scorecard_parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Skip judge scoring (drafting-only comparison)",
    )

    prove_parser = sub.add_parser(
        "prove",
        help="Run a project through every available provider, judge each, "
        "and write a head-to-head scorecard (skips unkeyed providers gracefully)",
    )
    prove_parser.add_argument(
        "--project",
        "-p",
        required=True,
        help="Path to ProjectInput YAML or alias: socson, inegol, rice",
    )
    prove_parser.add_argument(
        "--providers",
        default="auto",
        help="Comma-separated provider names or 'auto' (default: auto)",
    )
    prove_parser.add_argument(
        "--output",
        default="reports/provider-scorecard.md",
        help="Output markdown path (default: reports/provider-scorecard.md)",
    )
    prove_parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Skip judge scoring (drafting-only comparison)",
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
    benchmark_parser.add_argument(
        "--provider",
        default="demo",
        help="LLM provider name for benchmark drafting: demo, openai, anthropic (default: demo)",
    )
    benchmark_parser.add_argument(
        "--demo-output-dir",
        help="Optional client-demo publication root for benchmark DOCX packages",
    )

    workbook_fetch_parser = sub.add_parser(
        "fetch-workbook", help="Download the Vietnam WTE spreadsheet into the local cache"
    )
    workbook_fetch_parser.add_argument(
        "--mapping-config",
        default="configs/source_mappings/vietnam_wte_projects.yaml",
        help="Spreadsheet mapping config path",
    )
    workbook_fetch_parser.add_argument(
        "--cache-dir",
        default="data/source_inputs/spreadsheets",
        help="Workbook cache directory",
    )
    workbook_fetch_parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if the workbook is already cached",
    )

    spreadsheet_map_parser = sub.add_parser(
        "map-spreadsheet",
        help="Profile the workbook, select a Vietnam candidate row, and write ProjectInput artifacts",
    )
    spreadsheet_map_parser.add_argument(
        "--workbook",
        help="Path to a local workbook; if omitted the CLI fetches the configured workbook first",
    )
    spreadsheet_map_parser.add_argument(
        "--mapping-config",
        default="configs/source_mappings/vietnam_wte_projects.yaml",
        help="Spreadsheet mapping config path",
    )
    spreadsheet_map_parser.add_argument(
        "--candidate",
        default="soc-son",
        help="Candidate key from the mapping config",
    )
    spreadsheet_map_parser.add_argument(
        "--output-dir",
        help="Optional output directory for generated profile, snapshot, YAML, and report artifacts",
    )

    vietnam_run_parser = sub.add_parser(
        "run-vietnam-pdd",
        help="Run the full Vietnam spreadsheet-to-draft-review-DOCX workflow",
    )
    vietnam_run_parser.add_argument(
        "--mapping-config",
        default="configs/source_mappings/vietnam_wte_projects.yaml",
        help="Spreadsheet mapping config path",
    )
    vietnam_run_parser.add_argument(
        "--cache-dir",
        default="data/source_inputs/spreadsheets",
        help="Workbook cache directory",
    )
    vietnam_run_parser.add_argument(
        "--candidate",
        default="soc-son",
        help="Candidate key from the mapping config",
    )
    vietnam_run_parser.add_argument(
        "--provider",
        default="noop",
        help="LLM provider name for drafting: noop, demo, corpus, openai, anthropic (default: noop)",
    )
    vietnam_run_parser.add_argument(
        "--review-output-dir",
        help="Optional reviewer-facing publication root for published review packages",
    )
    vietnam_run_parser.add_argument(
        "--upload-review-docx",
        action="store_true",
        help="Upload the published reviewer-facing DOCX after workflow completion",
    )
    vietnam_run_parser.add_argument(
        "--folder-id",
        default="1pp23yRZ8qtopw1BPXrzVewXsmmWplCse",
        help="Target Drive folder ID for optional reviewer-facing upload",
    )

    extract_parser = sub.add_parser(
        "extract", help="Extract ProjectInput from a document (DOCX, PDF, or text)"
    )
    extract_parser.add_argument("file", help="Path to the document to extract from")
    extract_parser.add_argument(
        "--provider",
        default="noop",
        help="LLM provider name: noop, openai, anthropic (default: noop)",
    )
    extract_parser.add_argument(
        "--output", "-o", help="Optional output YAML path for extracted ProjectInput"
    )

    screen_parser = sub.add_parser(
        "screen", help="Screen a document or ProjectInput for applicable methodologies"
    )
    screen_parser.add_argument("file", help="Path to a document or ProjectInput YAML")
    screen_parser.add_argument(
        "--top-k", type=int, default=5, help="Max methodology suggestions (default: 5)"
    )
    screen_parser.add_argument(
        "--provider",
        default="noop",
        help="Provider for LLM applicability analysis: noop, openai, anthropic (noop = deterministic)",
    )

    draft_parser.add_argument(
        "--from-doc",
        help="Path to a document to extract ProjectInput from before drafting",
    )

    calc_parser = sub.add_parser(
        "calc",
        help="Compute methodology quantification for a ProjectInput without any LLM call",
    )
    calc_parser.add_argument(
        "--input",
        required=True,
        help="Path to a ProjectInput YAML file",
    )
    calc_parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write the result as JSON",
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
    load_dotenv(find_dotenv(usecwd=True))
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
        "demo-setup": lambda: _run_demo_setup(args, log),
        "draft": lambda: _run_draft(args, log),
        "calc": lambda: _run_calc(args, log),
        "review": lambda: _run_review(args, log),
        "judge": lambda: _run_judge(args, log),
        "export": lambda: _run_export(args, log),
        "upload": lambda: _run_upload(args, log),
        "demo-config": lambda: _run_demo_config(args, log),
        "fetch-registry": lambda: _run_fetch_registry(args, log),
        "scorecard": lambda: _run_scorecard(args, log),
        "prove": lambda: _run_prove(args, log),
        "benchmark": lambda: _run_benchmark(args, log),
        "fetch-workbook": lambda: _run_fetch_workbook(args, log),
        "map-spreadsheet": lambda: _run_map_spreadsheet(args, log),
        "run-vietnam-pdd": lambda: _run_vietnam_pdd(args, log),
        "extract": lambda: _run_extract(args, log),
        "screen": lambda: _run_screen(args, log),
        "doctor": run_doctor,
    }

    try:
        result = commands[args.command]()
        return result if isinstance(result, int) else 0
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


def _run_demo_setup(args, log) -> None:
    from pdd_agent.demo_setup import build_demo_index

    log.info("demo_setup_start")
    build_demo_index()
    log.info("demo_setup_done")


def _run_draft(args, log) -> None:
    from pdd_agent.llm.provider import get_provider_registry

    _configure_api_provider(args.provider)
    provider = get_provider_registry().get(args.provider)

    if hasattr(args, "from_doc") and args.from_doc:
        from pdd_agent.ingest.extract import extract_project_input

        doc_path = Path(args.from_doc)
        log.info("draft_from_doc_start", doc=str(doc_path))
        project_input = extract_project_input(doc_path, provider)
        log.info("extraction_complete", project=project_input.project.project_name)
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            log.error("input_file_not_found", path=str(input_path))
            return

        with open(input_path, encoding="utf-8") as f:
            input_data = yaml.safe_load(f)
        project_input = ProjectInput.model_validate(input_data)

    orchestrator = SectionOrchestrator(
        provider=provider,
        project_input=project_input,
        run_id=args.run_id,
        enable_judge=args.judge,
        max_redraft_attempts=3,
    )

    if args.provider not in ("demo", "noop"):
        from pdd_agent.calc.dispatch import compute_for

        calc_result = compute_for(project_input)
        if calc_result is not None:
            orchestrator.set_calc_result(calc_result)
            log.info(
                "calc_engine_ready",
                methodology_id=calc_result.methodology_id,
                net_tco2e=calc_result.net_emission_reductions_tco2e,
            )
        else:
            log.info("calc_engine_skipped", reason="compute_for returned None")

    if not (hasattr(args, "from_doc") and args.from_doc):
        input_path = Path(args.input)
        assumptions_path = resolve_assumptions_path(input_path)
        if assumptions_path:
            orchestrator.attach_assumption_register(load_assumption_register(assumptions_path))

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


def _run_calc(args, log) -> None:
    import json as _json

    from pdd_agent.calc.dispatch import compute_for

    input_path = Path(args.input)
    if not input_path.exists():
        log.error("input_file_not_found", path=str(input_path))
        return

    with open(input_path, encoding="utf-8") as f:
        input_data = yaml.safe_load(f)
    project_input = ProjectInput.model_validate(input_data)

    result = compute_for(project_input)
    if result is None:
        missing = []
        mid = (
            project_input.technology.methodology_ids[0].strip().upper()
            if project_input.technology.methodology_ids
            else ""
        )
        if mid == "ACM0022":
            if project_input.quantification.grid_emission_factor is None:
                missing.append("quantification.grid_emission_factor")
            if not project_input.quantification.grid_emission_factor_source:
                missing.append("quantification.grid_emission_factor_source")
        log.info("calc_inputs_incomplete", methodology_id=mid, missing=missing)
        print(f"Calc inputs incomplete for methodology {mid}: missing {', '.join(missing)}")
        return

    print(f"Methodology: {result.methodology_id}")
    print(f"Baseline emissions: {result.baseline_emissions_tco2e:,.2f} tCO2e/year")
    print(f"Project emissions: {result.project_emissions_tco2e:,.2f} tCO2e/year")
    print(f"Leakage: {result.leakage_tco2e:,.2f} tCO2e/year")
    print(f"Net emission reductions: {result.net_emission_reductions_tco2e:,.2f} tCO2e/year")
    print(
        f"Crediting period total: {result.crediting_period_total_tco2e:,.2f} tCO2e "
        f"({result.crediting_period_years} years)"
    )
    print(f"\nComponents ({len(result.components)}):")
    for comp in result.components:
        print(f"  - {comp.name}: {comp.value_tco2e:,.2f} {comp.unit} — {comp.formula}")
    print(f"\nMonitoring parameters: {len(result.monitoring_params)}")
    for param in result.monitoring_params:
        print(
            f"  - {param.get('id', '')}: {param.get('name', '')} "
            f"({param.get('unit', '')}, {param.get('frequency', '')})"
        )
    if result.annual_schedule:
        print(f"\nAnnual schedule ({len(result.annual_schedule)} years):")
        for entry in result.annual_schedule:
            print(f"Year {entry.year}: {entry.net_tco2e:,.2f} tCO2e")
    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for w in result.warnings:
            print(f"  - {w}")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "methodology_id": result.methodology_id,
            "baseline_emissions_tco2e": result.baseline_emissions_tco2e,
            "project_emissions_tco2e": result.project_emissions_tco2e,
            "leakage_tco2e": result.leakage_tco2e,
            "net_emission_reductions_tco2e": result.net_emission_reductions_tco2e,
            "crediting_period_total_tco2e": result.crediting_period_total_tco2e,
            "crediting_period_years": result.crediting_period_years,
            "components": [
                {
                    "name": c.name,
                    "value_tco2e": c.value_tco2e,
                    "unit": c.unit,
                    "formula": c.formula,
                    "notes": c.notes,
                }
                for c in result.components
            ],
            "warnings": result.warnings,
            "monitoring_params": result.monitoring_params,
            "annual_schedule": [
                {
                    "year": e.year,
                    "baseline_tco2e": e.baseline_tco2e,
                    "project_tco2e": e.project_tco2e,
                    "leakage_tco2e": e.leakage_tco2e,
                    "net_tco2e": e.net_tco2e,
                }
                for e in result.annual_schedule
            ],
        }
        output_path.write_text(_json.dumps(data, indent=2), encoding="utf-8")
        log.info("calc_output_written", path=str(output_path))


def _run_review(args, log) -> None:
    from pdd_agent.review.states import ReviewStateStore

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            ProjectInput.model_validate(yaml.safe_load(f))

    try:
        store = ReviewStateStore.load(args.run_id)
        log.info("review_state_loaded", run_id=args.run_id, state_count=len(store.sections))
        for key, sec in store.sections.items():
            log.info("section_state", key=key, state=sec.state.value)
    except FileNotFoundError:
        log.warning("no_review_state_found", run_id=args.run_id)


def _run_judge(args, log) -> None:
    from pdd_agent.llm.provider import DraftRun
    from pdd_agent.review.judge import LLMJudge

    run = DraftRun.load(args.run_id)
    log.info("judge_run_start", run_id=args.run_id, provider=run.provider)

    project_input = None
    if args.input:
        with open(args.input, encoding="utf-8") as f:
            project_input = ProjectInput.model_validate(yaml.safe_load(f))

    judge = LLMJudge(
        provider_name=run.provider,
        methodology_ids=(
            list(project_input.technology.methodology_ids)
            if project_input and project_input.technology.methodology_ids
            else None
        ),
    )
    results = judge.judge_run(run, project_input)

    passed = sum(1 for r in results.values() if r.passed)
    total = len(results)
    critical = sum(len(r.categories.get("critical", [])) for r in results.values())
    advisory = sum(len(r.categories.get("advisory", [])) for r in results.values())

    print(f"\nJudge summary for run {args.run_id}")
    print(f"  Sections judged: {total}")
    print(f"  Passed:          {passed}")
    print(f"  Failed:          {total - passed}")
    print(f"  Critical findings: {critical}")
    print(f"  Advisory findings: {advisory}")
    print("\nPer-section scores:")
    for key, result in sorted(results.items()):
        status = "PASS" if result.passed else "FAIL"
        print(f"  {key:8} {status}  score={result.score}")
        for cat, messages in result.categories.items():
            for msg in messages:
                print(f"            [{cat}] {msg}")

    log.info(
        "judge_run_complete",
        run_id=args.run_id,
        sections=total,
        passed=passed,
        critical=critical,
        advisory=advisory,
    )


def _run_export(args, log) -> None:
    from pdd_agent.export.docx_export import ExportBlockedError

    project_input = None
    if getattr(args, "input", None):
        with open(args.input, encoding="utf-8") as f:
            project_input = ProjectInput.model_validate(yaml.safe_load(f))

    if args.review_output_dir:
        docx_path = publish_docx_run_for_review(
            run_id=args.run_id,
            project_name=args.run_id,
            output_root=Path(args.review_output_dir),
        )
        log.info(
            "review_docx_published",
            path=str(docx_path),
            review_output_dir=str(args.review_output_dir),
        )
    else:
        output_path = Path(args.output) if args.output else None
        try:
            docx_path = export_run_to_docx(
                run_id=args.run_id,
                output_path=output_path,
                project_input=project_input,
                force=getattr(args, "force", False),
            )
        except ExportBlockedError as exc:
            log.error("export_blocked", run_id=args.run_id, error=str(exc))
            print(f"Export blocked: {exc}")
            return
        log.info("docx_exported", path=str(docx_path), force=getattr(args, "force", False))

    pdf_status = "not_requested"
    pdf_path = None
    if getattr(args, "pdf", False):
        try:
            pdf_path = export_docx_to_pdf(Path(docx_path))
            pdf_status = "created"
        except PDFExportError as exc:
            pdf_status = "skipped"
            log.warning("pdf_export_skipped", reason=str(exc))
    log.info(
        "export_complete",
        docx_path=str(docx_path),
        pdf_status=pdf_status,
        pdf_path=str(pdf_path) if pdf_path else None,
    )


def _run_upload(args, log) -> None:
    if args.review_docx:
        log.info("upload_start", review_docx=args.review_docx, folder=args.folder_id)
        result = upload_review_package_docx(
            Path(args.review_docx),
            drive_folder_id=args.folder_id,
        )
    else:
        log.info("upload_start", run_id=args.run_id, folder=args.folder_id)
        result = upload_docx_run(run_id=args.run_id, drive_folder_id=args.folder_id)
    if result["success"]:
        log.info("upload_success", drive_url=result["drive_url"])
    else:
        log.error("upload_failed", error=result["error"])


def _run_demo_config(args, log) -> None:
    path = create_demo_project_input(Path(args.output))
    log.info("demo_config_written", path=str(path))


def _run_scorecard(args, log) -> None:
    from pdd_agent.phase05.provider_scorecard import run_provider_scorecard

    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    output_path = run_provider_scorecard(
        input_path=Path(args.input),
        providers=providers,
        output_path=Path(args.output),
        enable_judge=not args.no_judge,
    )
    log.info("scorecard_complete", output=str(output_path), providers=providers)


def _run_prove(args, log) -> None:
    from pdd_agent.phase05.provider_scorecard import run_provider_scorecard

    project_aliases = {
        "socson": "configs/projects/demo_socson_like.yaml",
        "inegol": "configs/demo/inegol_project_input.yaml",
        "rice": "configs/projects/rice_vm0051_pilot.yaml",
    }
    project_path = project_aliases.get(args.project.lower(), args.project)
    input_path = Path(project_path)
    if not input_path.exists():
        log.error("prove_project_not_found", project=args.project, path=str(input_path))
        raise SystemExit(1)

    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    output_path = run_provider_scorecard(
        input_path=input_path,
        providers=providers,
        output_path=Path(args.output),
        enable_judge=not args.no_judge,
    )
    log.info(
        "prove_complete",
        project=args.project,
        output=str(output_path),
        providers=providers,
    )


def _run_fetch_registry(args, log) -> None:
    from pdd_agent.ingest.registry_download import download_registered_pdds

    records = download_registered_pdds(
        methodology_id=args.methodology,
        output_dir=Path(args.output_dir),
        limit=args.limit,
    )
    if records:
        log.info(
            "fetch_registry_complete",
            methodology=args.methodology,
            downloaded=len(records),
            output_dir=args.output_dir,
        )
    else:
        log.info(
            "fetch_registry_manual_mode",
            methodology=args.methodology,
            output_dir=args.output_dir,
            note="See manifest.json for manual-download instructions.",
        )


def _run_benchmark(args, log) -> None:
    _configure_api_provider(args.provider)
    artifacts = run_demo_benchmark(
        project_input_path=Path(args.input),
        reference_norm_path=Path(args.reference) if args.reference else None,
        reports_dir=Path(args.reports_dir),
        existing_run_path=Path(args.existing_run) if args.existing_run else None,
        provider_name=args.provider,
        export_docx=not args.no_export,
        demo_output_dir=Path(args.demo_output_dir) if args.demo_output_dir else None,
    )
    log.info(
        "benchmark_complete",
        run_id=artifacts.run_id,
        scorecard=str(artifacts.demo_scorecard),
        diff=str(artifacts.section_diff),
        demo_package_manifest=str(artifacts.demo_package_manifest)
        if artifacts.demo_package_manifest
        else None,
        demo_latest_docx=str(artifacts.demo_latest_docx) if artifacts.demo_latest_docx else None,
        runtime_seconds=artifacts.runtime_seconds,
        matched_sections=artifacts.comparison_summary.get("matched_sections"),
    )


def _run_fetch_workbook(args, log) -> None:
    workbook_path = fetch_workbook(
        mapping_config_path=Path(args.mapping_config),
        cache_dir=Path(args.cache_dir),
        force=args.force,
    )
    log.info("workbook_ready", path=str(workbook_path))


def _run_map_spreadsheet(args, log) -> None:
    workbook_path = (
        Path(args.workbook) if args.workbook else fetch_workbook(Path(args.mapping_config))
    )
    artifacts = generate_project_artifacts(
        workbook_path=workbook_path,
        mapping_config_path=Path(args.mapping_config),
        candidate_key=args.candidate,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    log.info(
        "spreadsheet_mapping_complete",
        workbook=str(artifacts.workbook_path),
        project_yaml=str(artifacts.project_yaml_path),
        assumptions_yaml=str(artifacts.assumptions_yaml_path),
        profile=str(artifacts.profile_json_path),
        snapshot=str(artifacts.snapshot_json_path),
        report=str(artifacts.report_path),
    )


def _run_vietnam_pdd(args, log) -> None:
    _configure_api_provider(args.provider)
    artifacts = run_vietnam_pdd_workflow(
        mapping_config_path=Path(args.mapping_config),
        cache_dir=Path(args.cache_dir),
        candidate_key=args.candidate,
        provider_name=args.provider,
        review_package_dir=Path(args.review_output_dir) if args.review_output_dir else None,
        upload_review_docx=args.upload_review_docx,
        drive_folder_id=args.folder_id,
    )
    log.info(
        "vietnam_pdd_workflow_complete",
        run_id=artifacts.run_id,
        project_yaml=str(artifacts.project_yaml_path),
        assumptions_yaml=str(artifacts.assumptions_yaml_path),
        draft_run=str(artifacts.draft_run_path),
        review_state=str(artifacts.review_state_path),
        review_docx=str(artifacts.docx_path),
        review_package_manifest=str(artifacts.review_package_manifest_path),
        latest_review_docx=str(artifacts.latest_docx_path),
        validation_report=str(artifacts.validation_report_path),
        gap_analysis=str(artifacts.gap_analysis_path),
        runbook=str(artifacts.runbook_path),
        upload_result=artifacts.upload_result,
    )


def _run_extract(args, log) -> None:
    from pdd_agent.ingest.extract import extract_project_input
    from pdd_agent.llm.provider import get_provider_registry

    _configure_api_provider(args.provider)

    doc_path = Path(args.file)
    if not doc_path.exists():
        log.error("file_not_found", path=str(doc_path))
        return

    provider = get_provider_registry().get(args.provider)
    project_input = extract_project_input(doc_path, provider)

    print(project_input.summary())

    if project_input.extraction_provenance:
        prov = project_input.extraction_provenance
        print("\nExtraction provenance:")
        print(f"  Extracted fields: {len(prov.extracted_fields)}")
        print(f"  Defaulted fields: {len(prov.defaulted_fields)}")
        print(f"  Missing fields:   {len(prov.missing_fields)}")
        if prov.missing_fields:
            print(f"  Missing: {', '.join(prov.missing_fields[:10])}")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                project_input.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                allow_unicode=True,
            )
        log.info("extracted_yaml_saved", path=str(output_path))


def _run_screen(args, log) -> None:
    from pdd_agent.domain.methodology_screen import screen_methodologies
    from pdd_agent.llm.provider import get_provider_registry

    _configure_api_provider(args.provider)

    file_path = Path(args.file)
    if not file_path.exists():
        log.error("file_not_found", path=str(file_path))
        return

    project_input = None
    if file_path.suffix in (".yaml", ".yml"):
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        try:
            project_input = ProjectInput.model_validate(data)
            description = project_input.summary()
        except Exception:
            description = file_path.read_text(encoding="utf-8")
    else:
        description = file_path.read_text(encoding="utf-8")

    provider = get_provider_registry().get(args.provider)
    suggestions = screen_methodologies(
        description,
        project_input=project_input,
        top_k=args.top_k,
        llm_provider=None if provider.name == "noop" else provider,
    )

    print(f"\nMethodology Screening Results ({len(suggestions)} suggestions):\n")
    for i, s in enumerate(suggestions, 1):
        print(f"  {i}. {s.methodology_id} — {s.name}")
        print(f"     Confidence: {s.confidence:.1%}")
        print(f"     Rationale:  {s.rationale}")
        print(f"     Version:    {s.version or 'unknown'}")
        print()


if __name__ == "__main__":
    sys.exit(main())
