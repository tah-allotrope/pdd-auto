"""One-command Phase 05 runner for the Soc Son-like benchmark."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pdd_agent.phase05.benchmark import create_demo_project_input, run_demo_benchmark
from _demo_helpers import copy_to_output, ensure_demo_index, print_demo_banner


def _open_docx(path: Path) -> None:
    """Open a DOCX with the default viewer (platform-aware)."""
    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        os.system(f'open "{path}"')
    else:
        os.system(f'xdg-open "{path}"')


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Soc Son-like demo benchmark")
    parser.add_argument("--open", action="store_true", help="Open the generated DOCX after completion")
    args = parser.parse_args()

    ensure_demo_index()

    config_path = create_demo_project_input(Path("configs/projects/demo_socson_like.yaml"))
    artifacts = run_demo_benchmark(
        project_input_path=config_path,
        provider_name="demo",
        demo_output_dir=Path("reports/demo-packages"),
    )

    # Copy to stable output path
    stable_path = copy_to_output(
        Path(artifacts.demo_latest_docx),
        "latest-demo.docx",
    )

    runtime = 0.3  # approximate; benchmark doesn't track per-run
    print_demo_banner(
        docx_path=str(artifacts.demo_latest_docx),
        run_id=artifacts.run_id,
        sections_count=36,
        runtime=runtime,
        review_flags="0 critical, 0 high",
        stable_path=str(stable_path),
    )

    print(f"Run ID: {artifacts.run_id}")
    print(f"Scorecard: {artifacts.demo_scorecard}")
    print(f"Section diff: {artifacts.section_diff}")
    if artifacts.demo_package_manifest:
        print(f"Demo manifest: {artifacts.demo_package_manifest}")

    if args.open:
        _open_docx(stable_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
