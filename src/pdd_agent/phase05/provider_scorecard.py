"""Head-to-head provider scorecard: run the same ProjectInput through N
drafting providers and judge every section, writing a markdown comparison.

Providers whose keys are missing (openai/anthropic without the matching
``{PROVIDER}_API_KEY``) are skipped with a logged warning, not a crash — the
scorecard always completes for whatever providers were actually usable.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
import yaml

from pdd_agent.agent.section_orchestrator import SectionOrchestrator
from pdd_agent.llm.budget import BudgetExhaustedError, TokenBudget
from pdd_agent.llm.env_config import configure_provider_from_env
from pdd_agent.llm.provider import get_provider_registry
from pdd_agent.review.judge import LLMJudge
from schemas.project_input import ProjectInput

logger = structlog.get_logger()


@dataclass
class ProviderScorecardRow:
    """Aggregate metrics for one provider's run against the same input."""

    provider: str
    sections_drafted: int = 0
    judge_pass_rate_pct: float = 0.0
    mean_judge_score: float = 0.0
    redraft_count: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    wall_clock_seconds: float = 0.0
    skipped_reason: str | None = None
    findings: list[str] = field(default_factory=list)


def _is_provider_available(provider_name: str) -> tuple[bool, str | None]:
    if provider_name in ("demo", "noop", "ollama"):
        return True, None
    if provider_name in ("openai", "anthropic"):
        if not os.environ.get(f"{provider_name.upper()}_API_KEY"):
            return False, "missing_api_key"
        return True, None
    return False, "unknown_provider"


def _run_one_provider(
    provider_name: str,
    project_input: ProjectInput,
    enable_judge: bool,
) -> ProviderScorecardRow:
    row = ProviderScorecardRow(provider=provider_name)
    start = time.perf_counter()

    configure_provider_from_env(provider_name)
    provider = get_provider_registry().get(provider_name)
    budget = TokenBudget(
        max_tokens=500_000,
        max_cost_usd=_parse_positive_float(os.environ.get("PDD_MAX_COST_USD")),
    )

    orchestrator = SectionOrchestrator(
        provider=provider,
        project_input=project_input,
        token_budget=budget,
        enable_judge=False,  # score separately below for per-provider metrics
    )

    try:
        run = orchestrator.run()
    except BudgetExhaustedError as exc:
        row.skipped_reason = f"budget_exhausted: {exc}"
        row.wall_clock_seconds = round(time.perf_counter() - start, 2)
        return row

    row.sections_drafted = len(run.sections)
    row.total_tokens = budget.total_tokens
    row.estimated_cost_usd = round(budget.estimated_cost_usd, 4)

    if enable_judge:
        judge_provider_name = os.environ.get("PDD_JUDGE_PROVIDER", provider_name)
        judge = LLMJudge(
            provider_name=judge_provider_name,
            use_llm=judge_provider_name not in ("demo", "noop"),
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

    row.wall_clock_seconds = round(time.perf_counter() - start, 2)
    return row


def _parse_positive_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _render_scorecard(rows: list[ProviderScorecardRow], input_path: Path) -> str:
    lines = [
        "# Provider Scorecard",
        "",
        f"- Input: `{input_path}`",
        "",
        "| Provider | Sections drafted | Judge pass rate | Mean judge score | Redraft count | Total tokens | Est. cost (USD) | Wall clock (s) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        if row.skipped_reason:
            lines.append(f"| {row.provider} | — skipped: {row.skipped_reason} | | | | | | |")
            continue
        lines.append(
            f"| {row.provider} | {row.sections_drafted} | {row.judge_pass_rate_pct}% | "
            f"{row.mean_judge_score} | {row.redraft_count} | {row.total_tokens} | "
            f"${row.estimated_cost_usd} | {row.wall_clock_seconds} |"
        )
    lines.append("")
    for row in rows:
        if row.findings:
            lines.append(f"## {row.provider} — critical findings")
            for finding in row.findings[:20]:
                lines.append(f"- {finding}")
            lines.append("")
    return "\n".join(lines) + "\n"


def run_provider_scorecard(
    input_path: Path,
    providers: list[str],
    output_path: Path,
    enable_judge: bool = True,
) -> Path:
    """Run the same ProjectInput through each provider and write a scorecard.

    Providers without a configured API key are skipped with a logged warning
    rather than raising. Returns output_path.
    """
    with open(input_path, encoding="utf-8") as f:
        project_input = ProjectInput.model_validate(yaml.safe_load(f))

    rows: list[ProviderScorecardRow] = []
    for provider_name in providers:
        available, reason = _is_provider_available(provider_name)
        if not available:
            logger.warning("scorecard_provider_skipped", provider=provider_name, reason=reason)
            rows.append(ProviderScorecardRow(provider=provider_name, skipped_reason=reason))
            continue
        logger.info("scorecard_provider_start", provider=provider_name)
        row = _run_one_provider(provider_name, project_input, enable_judge)
        rows.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_scorecard(rows, input_path), encoding="utf-8")
    return output_path
