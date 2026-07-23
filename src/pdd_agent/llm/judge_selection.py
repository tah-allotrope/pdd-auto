"""Shared never-self-judge provider-selection logic.

Used by both `prove`'s post-hoc scorecard (`phase05/provider_scorecard.py`)
and the in-loop redraft judge (`agent/section_orchestrator.py`) so a
drafting provider is never selected to judge its own output in either call
site, and the two call sites can never diverge again.
"""

from __future__ import annotations

import os
import shutil
import urllib.error
import urllib.request

# Preference order for cross-judging: the first provider in this list that is
# available and is not the drafting provider itself judges that provider's
# output. Falls back to the deterministic demo judge when nothing else
# qualifies, so a provider is never scored by itself.
JUDGE_PREFERENCE_ORDER = ["anthropic", "openai", "claude-code", "ollama"]


def _parse_positive_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def probe_ollama_available() -> tuple[bool, str | None]:
    """Real reachability probe (mirrors doctor.check_ollama), not a hardcoded True.

    A machine with no Ollama instance running previously got an "available"
    Ollama row full of `[OLLAMA ERROR ...]` placeholder sections presented as
    a real run — this probe makes "available" mean "answered".
    """
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        request = urllib.request.Request(f"{base_url}/api/tags")
        with urllib.request.urlopen(request, timeout=2):
            pass
        return True, None
    except (urllib.error.URLError, OSError, TimeoutError):
        return False, "ollama_unreachable"


def is_provider_available(provider_name: str) -> tuple[bool, str | None]:
    if provider_name in ("demo", "noop"):
        return True, None
    if provider_name == "ollama":
        return probe_ollama_available()
    if provider_name == "claude-code":
        # Subscription-billed: no PDD_MAX_COST_USD gate, just presence of the
        # CLI on PATH.
        cli = os.environ.get("CLAUDE_CODE_CLI", "claude")
        if shutil.which(cli) is None:
            return False, "claude_cli_not_found"
        return True, None
    if provider_name in ("openai", "anthropic"):
        if not os.environ.get(f"{provider_name.upper()}_API_KEY"):
            return False, "missing_api_key"
        if _parse_positive_float(os.environ.get("PDD_MAX_COST_USD")) is None:
            return False, "missing_cost_ceiling"
        return True, None
    return False, "unknown_provider"


def select_judge_provider(
    drafting_provider: str, available_providers: list[str]
) -> tuple[str, bool]:
    """Resolve which provider judges `drafting_provider`'s output (never itself).

    Order: PDD_JUDGE_PROVIDER env override, then the first provider in
    `available_providers` that appears in JUDGE_PREFERENCE_ORDER and isn't
    the drafting provider, else the deterministic demo judge.

    Use this form when the caller already has a precomputed availability
    list for the whole run (e.g. the scorecard, which checks every requested
    provider once up front) — it does no probing of its own.
    """
    env_override = os.environ.get("PDD_JUDGE_PROVIDER")
    if env_override:
        return env_override, env_override not in ("demo", "noop")

    for candidate in JUDGE_PREFERENCE_ORDER:
        if candidate == drafting_provider:
            continue
        if candidate in available_providers:
            return candidate, True

    return "demo", False


def resolve_judge_provider(drafting_provider: str) -> tuple[str, bool]:
    """Resolve the judge provider for a single drafting provider, probing live.

    Convenience wrapper for callers (like the per-section redraft loop) that
    don't already have a precomputed availability list: probes each
    JUDGE_PREFERENCE_ORDER candidate via is_provider_available(), then
    delegates to select_judge_provider() for the actual selection.
    """
    available = [p for p in JUDGE_PREFERENCE_ORDER if is_provider_available(p)[0]]
    return select_judge_provider(drafting_provider, available)
