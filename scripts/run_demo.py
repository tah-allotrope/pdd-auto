"""One-command Phase 05 runner for the Soc Son-like benchmark."""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pdd_agent.phase05.benchmark import create_demo_project_input, run_demo_benchmark


def main() -> int:
    config_path = create_demo_project_input(Path("configs/projects/demo_socson_like.yaml"))
    artifacts = run_demo_benchmark(project_input_path=config_path)
    print(f"Run ID: {artifacts.run_id}")
    print(f"Scorecard: {artifacts.demo_scorecard}")
    print(f"Section diff: {artifacts.section_diff}")
    if artifacts.export_docx:
        print(f"DOCX: {artifacts.export_docx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
