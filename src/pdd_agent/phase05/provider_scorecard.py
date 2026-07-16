"""Head-to-head provider scorecard: run the same ProjectInput through N
drafting providers and judge every section, writing a markdown comparison.

Providers whose keys are missing (openai/anthropic without the matching
``{PROVIDER}_API_KEY``) or whose cost ceiling is unset, and Ollama when no
local instance answers, are skipped with a logged warning, not a crash — the
scorecard always completes for whatever providers were actually usable, and
any provider that crashes mid-run is isolated to its own row rather than
aborting the whole scorecard.
"""

from __future__ import annotations

import os
import shutil
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import structlog
import yaml

from pdd_agent.agent.section_orchestrator import SectionOrchestrator
from pdd_agent.llm.budget import BudgetExhaustedError, TokenBudget
from pdd_agent.llm.env_config import configure_provider_from_env
from pdd_agent.llm.provider import get_provider_registry
from pdd_agent.review.judge import LLMJudge
from schemas.project_input import ProjectInput

logger = structlog.get_logger()

# Preference order for cross-judging (ASM-006): the first provider in this
# list that is available and is not the drafting provider itself judges that
# provider's output. Falls back to the deterministic demo judge when nothing
# else qualifies, so a provider is never scored by itself.
_JUDGE_PREFERENCE_ORDER = ["anthropic", "openai", "claude-code", "ollama"]


@dataclass
class ProviderScorecardRow:
    """Aggregate metrics for one provider's run against the same input."""

    provider: str
    sections_drafted: int = 0
    sections_failed: int = 0
    judge_pass_rate_pct: float = 0.0
    mean_judge_score: float = 0.0
    judge_provider: str = ""
    redraft_count: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    wall_clock_seconds: float = 0.0
    skipped_reason: str | None = None
    findings: list[str] = field(default_factory=list)


def _parse_positive_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _probe_ollama_available() -> tuple[bool, str | None]:
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


def _is_provider_available(provider_name: str) -> tuple[bool, str | None]:
    if provider_name in ("demo", "noop"):
        return True, None
    if provider_name == "ollama":
        return _probe_ollama_available()
    if provider_name == "claude-code":
        # Subscription-billed (ASM-007): no PDD_MAX_COST_USD gate, just
        # presence of the CLI on PATH.
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


def _select_judge_provider(
    drafting_provider: str, available_providers: list[str]
) -> tuple[str, bool]:
    """Resolve which provider judges `drafting_provider`'s output (never itself).

    Order: PDD_JUDGE_PROVIDER env override, then the first available provider
    in _JUDGE_PREFERENCE_ORDER that isn't the drafting provider, else the
    deterministic demo judge.
    """
    env_override = os.environ.get("PDD_JUDGE_PROVIDER")
    if env_override:
        return env_override, env_override not in ("demo", "noop")

    for candidate in _JUDGE_PREFERENCE_ORDER:
        if candidate == drafting_provider:
            continue
        if candidate in available_providers:
            return candidate, True

    return "demo", False


def _count_failed_sections(sections, provider_name: str) -> int:
    """Count sections whose text is a provider-error placeholder (DEC-002)."""
    prefix = f"[{provider_name.upper()} ERROR"
    return sum(1 for s in sections if s.text.startswith(prefix))


def _run_one_provider(
    provider_name: str,
    project_input: ProjectInput,
    enable_judge: bool,
    available_providers: list[str],
) -> ProviderScorecardRow:
    row = ProviderScorecardRow(provider=provider_name)
    start = time.perf_counter()

    try:
        configure_provider_from_env(provider_name)
        provider = get_provider_registry().get(provider_name)
        budget = TokenBudget(
            max_tokens=500_000,
            max_cost_usd=_parse_positive_float(os.environ.get("PDD_MAX_COST_USD")),
        )

        # Only real providers run the in-loop judge/redraft loop; demo/noop
        # stay deterministic (RISK-04-01) so existing demo artifacts and
        # tests are unaffected.
        drafting_enable_judge = enable_judge and provider_name not in ("demo", "noop")

        orchestrator = SectionOrchestrator(
            provider=provider,
            project_input=project_input,
            token_budget=budget,
            enable_judge=drafting_enable_judge,
        )

        run = orchestrator.run()

        row.sections_drafted = len(run.sections)
        row.sections_failed = _count_failed_sections(run.sections, provider_name)
        row.redraft_count = orchestrator.redraft_count

        if enable_judge:
            judge_provider_name, judge_use_llm = _select_judge_provider(
                provider_name, available_providers
            )
            configure_provider_from_env(judge_provider_name)
            row.judge_provider = judge_provider_name
            judge = LLMJudge(
                provider_name=judge_provider_name,
                use_llm=judge_use_llm,
                methodology_ids=(
                    list(project_input.technology.methodology_ids)
                    if project_input and project_input.technology.methodology_ids
                    else None
                ),
                token_budget=budget,
            )
            scores: list[int] = []
            passed_count = 0
            for section in run.sections:
                result = judge.judge_section(section, project_input)
                scores.append(result.score)
                if result.passed:
                    passed_count += 1
                else:
                    row.findings.extend(result.categories.get("critical", []))
            if scores:
                row.mean_judge_score = round(sum(scores) / len(scores), 1)
                row.judge_pass_rate_pct = round(100.0 * passed_count / len(scores), 1)

        # Assigned once, after drafting and any judging, so totals include
        # judge-call tokens (ASM-008) rather than only the drafting cost.
        row.total_tokens = budget.total_tokens
        row.estimated_cost_usd = round(budget.estimated_cost_usd, 4)
        row.wall_clock_seconds = round(time.perf_counter() - start, 2)
        return row
    except BudgetExhaustedError as exc:
        row.skipped_reason = f"budget_exhausted: {exc}"
        row.wall_clock_seconds = round(time.perf_counter() - start, 2)
        return row
    except Exception as exc:
        # A single provider's crash must not abort the whole scorecard — it
        # gets recorded as a failed row and every other provider still runs.
        logger.error("scorecard_provider_error", provider=provider_name, error=str(exc))
        row.skipped_reason = f"provider_error: {exc}"
        row.wall_clock_seconds = round(time.perf_counter() - start, 2)
        return row


def _render_row(row: ProviderScorecardRow) -> str:
    if row.skipped_reason:
        cells = [row.provider, f"— skipped: {row.skipped_reason}"] + [""] * 8
    else:
        cells = [
            row.provider,
            str(row.sections_drafted),
            str(row.sections_failed),
            f"{row.judge_pass_rate_pct}%",
            str(row.mean_judge_score),
            row.judge_provider or "—",
            str(row.redraft_count),
            str(row.total_tokens),
            f"${row.estimated_cost_usd}",
            str(row.wall_clock_seconds),
        ]
    return "| " + " | ".join(cells) + " |"


def _render_scorecard(
    rows: list[ProviderScorecardRow], input_path: Path, enable_judge: bool = True
) -> str:
    ran_rows = [r for r in rows if not r.skipped_reason]
    skipped_rows = [r for r in rows if r.skipped_reason]
    lines = [
        "# Provider Scorecard",
        "",
        f"- Input: `{input_path}`",
        f"- Providers ran: {len(ran_rows)}",
        f"- Providers skipped: {len(skipped_rows)}",
        "",
        "| Provider | Sections drafted | Sections failed | Judge pass rate | "
        "Mean judge score | Judge | Redraft count | Total tokens | "
        "Est. cost (USD) | Wall clock (s) |",
        "|---|---:|---:|---:|---:|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(_render_row(row))
    lines.append("")
    if enable_judge and any(r.provider not in ("demo", "noop") for r in ran_rows):
        lines.append(
            "_Judge tokens are included in Total tokens / Est. cost; in-loop "
            "redraft judging roughly doubles judge calls for real providers._"
        )
        lines.append("")
    if skipped_rows:
        lines.append("## Skipped providers")
        lines.append("")
        for row in skipped_rows:
            lines.append(f"- **{row.provider}**: {row.skipped_reason}")
        lines.append("")
    for row in ran_rows:
        if row.findings:
            lines.append(f"## {row.provider} — critical findings")
            for finding in row.findings[:20]:
                lines.append(f"- {finding}")
            lines.append("")
    return "\n".join(lines) + "\n"


_ALL_PROVIDERS = ["demo", "ollama", "claude-code", "openai", "anthropic"]


def _resolve_providers(providers: list[str] | str) -> list[str]:
    """Resolve provider list; 'auto' expands to all known providers."""
    if isinstance(providers, str):
        providers = [p.strip() for p in providers.split(",") if p.strip()]
    if providers == ["auto"] or providers == "auto":
        return list(_ALL_PROVIDERS)
    return providers


def run_provider_scorecard(
    input_path: Path,
    providers: list[str] | str,
    output_path: Path,
    enable_judge: bool = True,
) -> Path:
    """Run the same ProjectInput through each provider and write a scorecard.

    Providers without a configured API key, without a cost ceiling
    (``PDD_MAX_COST_USD``), or (for Ollama) that don't answer a live
    reachability probe are skipped with a logged warning rather than
    raising. ``providers`` may be ``"auto"`` to enumerate all known providers
    (demo, ollama, openai, anthropic), skipping unavailable ones gracefully.
    Returns output_path.
    """
    with open(input_path, encoding="utf-8") as f:
        project_input = ProjectInput.model_validate(yaml.safe_load(f))

    resolved = _resolve_providers(providers)
    availability = {p: _is_provider_available(p) for p in resolved}
    available_providers = [p for p, (ok, _) in availability.items() if ok]

    rows: list[ProviderScorecardRow] = []
    for provider_name in resolved:
        available, reason = availability[provider_name]
        if not available:
            logger.warning("scorecard_provider_skipped", provider=provider_name, reason=reason)
            rows.append(ProviderScorecardRow(provider=provider_name, skipped_reason=reason))
            continue
        logger.info("scorecard_provider_start", provider=provider_name)
        row = _run_one_provider(provider_name, project_input, enable_judge, available_providers)
        rows.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_scorecard(rows, input_path, enable_judge), encoding="utf-8")
    return output_path
