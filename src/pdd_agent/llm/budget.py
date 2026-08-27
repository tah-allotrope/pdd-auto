"""Per-run token budget tracking and cost estimation.

Enforces a configurable token limit per pipeline run to prevent
runaway LLM costs. Raises BudgetExhaustedError at 100% and logs
a warning at 80%.
"""

from __future__ import annotations

import threading
from pathlib import Path

import structlog
import yaml
from dataclasses import dataclass, field

logger = structlog.get_logger()


class BudgetExhaustedError(Exception):
    """Raised when the per-run token budget is fully consumed."""


@dataclass
class CallRecord:
    """Record of a single LLM API call."""

    section_id: str
    input_tokens: int
    output_tokens: int
    model: str = ""
    cost_usd: float = 0.0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0


# Pricing per 1M tokens (approximate as of 2025). Embedded fallback used only
# when configs/model_pricing.yaml is missing or unparseable.
_FALLBACK_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "claude-sonnet-5": {"input": 3.00, "output": 15.00},
    "claude-opus-4-8": {"input": 15.00, "output": 75.00},
    "claude-haiku-4-5-20251001": {"input": 0.25, "output": 1.25},
    "ollama-local": {"input": 0.0, "output": 0.0},
}

_PRICING_PATH = Path(__file__).parent.parent.parent.parent / "configs" / "model_pricing.yaml"


def _load_pricing(path: Path | None = None) -> dict[str, dict[str, float]]:
    """Load model pricing from configs/model_pricing.yaml.

    Falls back to the embedded _FALLBACK_PRICING dict if the file is missing
    or fails to parse, so pricing lookups never hard-fail.
    """
    pricing_path = path or _PRICING_PATH
    try:
        with open(pricing_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict) and data:
            return data
    except (OSError, yaml.YAMLError):
        pass
    return _FALLBACK_PRICING


_DEFAULT_PRICING = _load_pricing()


def estimate_run(
    section_budgets: dict[str, int],
    avg_prompt_chars: float,
    model: str,
    provider: str,
    overhead_tokens_per_section: int = 0,
) -> dict[str, float]:
    """Estimate input/output tokens and cost for a run."""
    sections = len(section_budgets)
    input_tokens = (
        round(sections * avg_prompt_chars / 3.5) + overhead_tokens_per_section * sections
        if sections
        else 0
    )
    output_tokens = round(sum(section_budgets.values()) / 3.5) if section_budgets else 0
    total_tokens = input_tokens + output_tokens
    _PROVIDER_FALLBACK_KEY = {"ollama": "ollama-local", "claude-code": "claude-code"}
    fallback_key = _PROVIDER_FALLBACK_KEY.get(provider, "gpt-4o")
    pricing = _DEFAULT_PRICING.get(model, _DEFAULT_PRICING.get(fallback_key, {}))
    input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0) if pricing else 0
    output_cost = (output_tokens / 1_000_000) * pricing.get("output", 0) if pricing else 0
    estimated_cost_usd = input_cost + output_cost
    return {
        "sections": sections,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": estimated_cost_usd,
    }


@dataclass
class TokenBudget:
    """Tracks token usage and cost against a per-run budget.

    Args:
        max_tokens: Hard limit for total tokens (input + output).
        max_cost_usd: Hard limit for total estimated cost.
        warning_threshold: Fraction at which a warning is logged (default 0.8).
    """

    max_tokens: int = 500_000
    max_cost_usd: float | None = None
    warning_threshold: float = 0.8
    calls: list[CallRecord] = field(default_factory=list)
    _warning_emitted: bool = field(default=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def total_cache_tokens(self) -> int:
        return sum(c.cache_creation_tokens + c.cache_read_tokens for c in self.calls)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens + self.total_cache_tokens

    @property
    def remaining(self) -> int:
        return max(0, self.max_tokens - self.total_tokens)

    @property
    def utilization(self) -> float:
        if self.max_tokens == 0:
            return 1.0
        return self.total_tokens / self.max_tokens

    @property
    def is_exhausted(self) -> bool:
        return self.total_tokens >= self.max_tokens

    @property
    def estimated_cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    def check_budget(self) -> None:
        """Check budget and raise/warn as appropriate. Call before each LLM request."""
        with self._lock:
            if self.is_exhausted:
                raise BudgetExhaustedError(
                    f"Token budget exhausted: {self.total_tokens:,} / {self.max_tokens:,} "
                    f"({len(self.calls)} calls, ${self.estimated_cost_usd:.4f})"
                )
            if self.max_cost_usd is not None and self.estimated_cost_usd >= self.max_cost_usd:
                raise BudgetExhaustedError(
                    f"Cost budget exhausted: ${self.estimated_cost_usd:.4f} / "
                    f"${self.max_cost_usd:.4f} ({len(self.calls)} calls, "
                    f"{self.total_tokens:,} tokens)"
                )
            if not self._warning_emitted and self.utilization >= self.warning_threshold:
                self._warning_emitted = True
                logger.warning(
                    "token_budget_warning",
                    utilization=f"{self.utilization:.1%}",
                    total_tokens=self.total_tokens,
                    max_tokens=self.max_tokens,
                    remaining=self.remaining,
                    calls=len(self.calls),
                )

    def record(
        self,
        section_id: str,
        input_tokens: int,
        output_tokens: int,
        model: str = "",
        provider: str = "",
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        cost_usd: float | None = None,
    ) -> CallRecord:
        """Record a completed LLM call and return the call record."""
        if cost_usd is not None:
            cost = cost_usd
        else:
            cost = self._estimate_cost(input_tokens, output_tokens, model, provider)
        record = CallRecord(
            section_id=section_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            cost_usd=cost,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
        )
        with self._lock:
            self.calls.append(record)
        logger.debug(
            "token_usage_recorded",
            section_id=section_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=self.total_tokens,
            utilization=f"{self.utilization:.1%}",
        )
        return record

    def _estimate_cost(
        self, input_tokens: int, output_tokens: int, model: str, provider: str = ""
    ) -> float:
        # claude-code is billed via the operator's subscription, not a
        # per-token API rate (ASM-007) — without this, its CLI model alias
        # (e.g. "sonnet") wouldn't match a pricing key and would silently
        # fall through to gpt-4o rates instead of $0.
        _PROVIDER_FALLBACK_KEY = {"ollama": "ollama-local", "claude-code": "claude-code"}
        fallback_key = _PROVIDER_FALLBACK_KEY.get(provider, "gpt-4o")
        pricing = _DEFAULT_PRICING.get(model, _DEFAULT_PRICING.get(fallback_key, {}))
        if not pricing:
            return 0.0
        input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0)
        output_cost = (output_tokens / 1_000_000) * pricing.get("output", 0)
        return input_cost + output_cost

    def summary(self) -> dict:
        """Return a summary dict suitable for run metadata."""
        return {
            "max_tokens": self.max_tokens,
            "max_cost_usd": self.max_cost_usd,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cache_tokens": self.total_cache_tokens,
            "total_tokens": self.total_tokens,
            "utilization": round(self.utilization, 4),
            "remaining": self.remaining,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "num_calls": len(self.calls),
            "exhausted": self.is_exhausted,
            "cost_ceiling_hit": (
                self.max_cost_usd is not None and self.estimated_cost_usd >= self.max_cost_usd
            ),
        }
