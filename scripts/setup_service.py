"""One-command setup script for the PDD Agent local service.

Checks the environment, installs dependencies, validates optional tooling,
and prints the command to launch the service.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _python_version_ok() -> bool:
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 11):
        print(f"ERROR: Python {major}.{minor} found; >=3.11 required.")
        return False
    print(f"OK: Python {major}.{minor}")
    return True


def _install_package() -> bool:
    print("Installing package with [dev,service,export] extras...")
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-e",
        ".[dev,service,export]",
    ]
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        print("ERROR: pip install failed.")
        return False
    print("OK: package installed")
    return True


def _check_command(name: str) -> bool:
    return shutil.which(name) is not None


def _check_optional_deps() -> None:
    print("\nOptional dependency checks:")
    if _check_command("soffice") or _check_command("libreoffice"):
        print("  OK: LibreOffice found (DOCX->PDF conversion available)")
    else:
        print("  WARN: LibreOffice not found; PDF export will be unavailable")

    if _check_command("gws"):
        print("  OK: gws CLI found (Google Workspace integration available)")
    else:
        print("  WARN: gws CLI not found; Drive upload/download will be unavailable")


def _validate_api_keys_if_requested() -> None:
    print("\nAPI provider key validation:")
    if os.environ.get("OPENAI_API_KEY"):
        print("  INFO: OPENAI_API_KEY is set")
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("  INFO: ANTHROPIC_API_KEY is set")
    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        print("  INFO: No API keys set. Service will use the demo provider by default.")

    if input("Validate API provider keys? [y/N] ").lower().startswith("y"):
        for provider in ("openai", "anthropic"):
            key = os.environ.get(f"{provider.upper()}_API_KEY")
            if key:
                print(f"  OK: {provider.upper()}_API_KEY is present")
            else:
                print(f"  WARN: {provider.upper()}_API_KEY is not set")
    else:
        print("  Skipped API key validation.")


def _print_launch_command() -> None:
    print("\n" + "=" * 60)
    print("Setup complete. Launch the service with:")
    print("  uvicorn pdd_agent.service.main:app --reload")
    print("=" * 60)


def main() -> int:
    print(f"PDD Agent service setup ({platform.system()})")
    print(f"Repository root: {REPO_ROOT}\n")

    if not _python_version_ok():
        return 1
    if not _install_package():
        return 1
    _check_optional_deps()
    _validate_api_keys_if_requested()
    _print_launch_command()
    return 0


if __name__ == "__main__":
    sys.exit(main())
