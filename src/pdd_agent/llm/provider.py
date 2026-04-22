"""Abstract LLM provider with local-first and noop fallbacks.

The tool ships with a noop provider (zero cost, human-in-the-loop review mode)
and a structured-output provider interface so API-backed models can be swapped in
without changing orchestration code.
"""

from __future__ import annotations

import json
import structlog
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = structlog.get_logger()


@dataclass
class DraftSection:
    """Output of a single section draft operation."""

    section_id: str
    sub_section_id: str
    text: str
    confidence: str  # HIGH | MEDIUM | LOW | UNSUPPORTED
    provenance: list[str]  # e.g. ["[CORPUS: VCS_Soc Son, 3.4 Baseline Scenario]"]
    issues: list[str]  # e.g. ["REVIEW: Baseline scenario requires site-specific evidence"]
    provider: str  # which provider produced this


@dataclass
class LLMResponse:
    """Wrapper for raw model output."""

    text: str
    provider: str
    model: str | None = None
    tokens_used: int | None = None
    cost_usd: float | None = None
    raw: dict[str, Any] | None = None


class BaseProvider(ABC):
    """Abstract base for all LLM providers."""

    name: str = "base"

    @abstractmethod
    def draft_section(
        self,
        section_id: str,
        sub_section_id: str,
        prompt: str,
        provenance: list[str],
        max_chars: int = 4000,
    ) -> DraftSection:
        """Draft a single section. Must include provenance markers in text."""
        ...

    @abstractmethod
    def close(self) -> None: ...


class NoopProvider(BaseProvider):
    """Zero-cost provider that emits structured placeholders instead of text.

    In human-in-the-loop mode this is the default. The placeholder output makes
    it clear exactly which sections need human authoring and what evidence
    is required.
    """

    name: str = "noop"

    def draft_section(
        self,
        section_id: str,
        sub_section_id: str,
        prompt: str,
        provenance: list[str],
        max_chars: int = 4000,
    ) -> DraftSection:
        prov_str = ", ".join(provenance) if provenance else "none"
        text = (
            f"[PLACEHOLDER — {section_id}"
            f"{'.' + sub_section_id if sub_section_id else ''}]\n"
            f"This section requires human authoring or project-specific evidence.\n"
            f"Relevant provenance: {prov_str}\n"
            f"Review sensitivity: see schemas/pdd_section_schema.yaml"
        )
        return DraftSection(
            section_id=section_id,
            sub_section_id=sub_section_id,
            text=text[:max_chars],
            confidence="UNSUPPORTED",
            provenance=provenance,
            issues=[
                f"REVIEW REQUIRED: {section_id}"
                f"{'.' + sub_section_id if sub_section_id else ''} — "
                f"human input or project-specific evidence needed before finalizing"
            ],
            provider=self.name,
        )

    def close(self) -> None:
        pass


@dataclass
class ModelConfig:
    """Configuration for a model provider."""

    provider_name: str
    model_name: str
    api_key: str | None = None
    base_url: str | None = None
    max_tokens: int = 4000
    temperature: float = 0.1


@dataclass
class ProviderRegistry:
    """Registry of available providers. Default = noop only."""

    providers: dict[str, BaseProvider] = field(default_factory=dict)
    _default: str = "noop"

    def register(self, name: str, provider: BaseProvider) -> None:
        self.providers[name] = provider

    def get(self, name: str) -> BaseProvider:
        if name not in self.providers:
            logger.warning("provider_not_found", name=name, available=list(self.providers.keys()))
            return self.providers[self._default]
        return self.providers[name]

    def default(self) -> BaseProvider:
        return self.providers[self._default]

    def close_all(self) -> None:
        for p in self.providers.values():
            p.close()


_registry: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
        _registry.register("noop", NoopProvider())
    return _registry


def configure_provider(config: ModelConfig) -> None:
    """Configure a provider from a ModelConfig and register it."""
    registry = get_provider_registry()
    if config.provider_name == "noop":
        registry.register("noop", NoopProvider())
    elif config.provider_name == "openai":
        from pdd_agent.llm.openai_provider import OpenAIProvider

        registry.register("openai", OpenAIProvider(config))
    elif config.provider_name == "ollama":
        from pdd_agent.llm.ollama_provider import OllamaProvider

        registry.register("ollama", OllamaProvider(config))
    else:
        logger.warning("unknown_provider", name=config.provider_name)


@dataclass
class DraftRun:
    """A complete per-run record of all drafted sections."""

    run_id: str
    project_name: str
    sections: list[DraftSection] = field(default_factory=list)
    provider: str = "noop"
    notes: list[str] = field(default_factory=list)

    def add(self, section: DraftSection) -> None:
        self.sections.append(section)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "project_name": self.project_name,
            "provider": self.provider,
            "sections": [
                {
                    "section_id": s.section_id,
                    "sub_section_id": s.sub_section_id,
                    "text": s.text,
                    "confidence": s.confidence,
                    "provenance": s.provenance,
                    "issues": s.issues,
                    "provider": s.provider,
                }
                for s in self.sections
            ],
            "notes": self.notes,
        }

    def save(self, output_dir: Path | None = None) -> Path:
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent.parent / "data" / "runs"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{self.run_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info("draft_run_saved", run_id=self.run_id, path=str(path))
        return path

    def summary(self) -> dict[str, Any]:
        total = len(self.sections)
        by_confidence: dict[str, int] = {}
        for s in self.sections:
            by_confidence[s.confidence] = by_confidence.get(s.confidence, 0) + 1
        issues_total = sum(len(s.issues) for s in self.sections)
        return {
            "run_id": self.run_id,
            "total_sections": total,
            "by_confidence": by_confidence,
            "total_issues": issues_total,
            "provider": self.provider,
        }
