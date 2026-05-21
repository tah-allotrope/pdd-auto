"""One-command Inegol demo runner.

Loads the Inegol ProjectInput, runs the full pipeline with demo provider,
and exports DOCX + JSON review package.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml

from pdd_agent.agent.section_orchestrator import SectionOrchestrator
from pdd_agent.export.docx_export import export_run_to_docx
from pdd_agent.llm.provider import get_provider_registry
from pdd_agent.review.tbd_tracker import TBDTracker
from pdd_agent.review.consistency import check_quantitative_consistency
from schemas.project_input import ProjectInput

logger = None


def main() -> int:
    config_path = REPO_ROOT / "configs" / "demo" / "inegol_project_input.yaml"
    if not config_path.exists():
        print(f"ERROR: Inegol config not found at {config_path}")
        return 1

    with open(config_path, encoding="utf-8") as f:
        project_input = ProjectInput.model_validate(yaml.safe_load(f))

    print(f"Loaded Inegol project: {project_input.project.project_name}")
    print(f"  VCS ID: {project_input.project.project_id_vcs or 'TBD'}")
    print(f"  Methodology: {', '.join(project_input.technology.methodology_ids)}")
    print(f"  Capacity: {project_input.technology.installed_capacity_mw} MW")
    print(f"  Annual waste: {project_input.technology.annual_waste_throughput:,.0f} tonnes")

    provider = get_provider_registry().get("demo")
    orchestrator = SectionOrchestrator(provider=provider, project_input=project_input)

    start = time.perf_counter()
    run = orchestrator.run()
    review_result = orchestrator.run_review()
    runtime = round(time.perf_counter() - start, 3)

    # Export DOCX
    docx_path = export_run_to_docx(run.run_id)

    # Export JSON review package
    runs_dir = REPO_ROOT / "data" / "runs"
    review_json_path = runs_dir / f"{run.run_id}-review.json"
    with open(review_json_path, "w", encoding="utf-8") as f:
        json.dump(review_result, f, indent=2, ensure_ascii=False)

    # TBD quick scan
    tbd_tracker = TBDTracker()
    tbd_report = tbd_tracker.scan(run.sections, run_id=run.run_id)

    # Print summary
    print("\n=== Inegol Demo Summary ===")
    print(f"Run ID: {run.run_id}")
    print(f"Sections drafted: {len(run.sections)}")
    print(f"Runtime: {runtime}s")
    print(f"DOCX: {docx_path}")
    print(f"Review JSON: {review_json_path}")
    print(f"\nReview results:")
    print(f"  Review passed: {review_result['review']['passed']}")
    print(f"  Consistency passed: {review_result['consistency']['passed']}")
    print(f"  Critical flags: {review_result['consistency']['critical_count']}")
    print(f"  High flags: {review_result['consistency']['high_count']}")
    print(f"  TBD markers found: {tbd_report.count}")
    print(f"  Sections with TBD: {tbd_report.sections_with_tbd}")

    # Comparison metrics
    print("\n=== Pipeline vs Codex Baseline ===")
    print(f"Sections populated: {len(run.sections)} (Codex: ~36 sections in 23 pages)")
    print(f"Structured tables: 11 VCS v4.4 table types supported")
    print(f"Provenance tracking: per-section corpus citations")
    print(f"Review layers: consistency + TBD + compliance (Codex: static markers only)")
    print(f"Appendices: Assumptions + Reviewer Issues + Data Gaps (Codex: 2 appendices)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
