"""Ollama local-model provider stub.

Wire this in by calling configure_provider() with a ModelConfig
where provider_name="ollama" and base_url points to a local Ollama instance.
Requires: ollama>=0.1.0
"""

from __future__ import annotations

from pdd_agent.llm.provider import BaseProvider, DraftSection, ModelConfig


class OllamaProvider(BaseProvider):
    """Ollama provider for local LLM inference."""

    name = "ollama"

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._base_url = config.base_url or "http://localhost:11434"

    def draft_section(
        self,
        section_id: str,
        sub_section_id: str,
        prompt: str,
        provenance: list[str],
        max_chars: int = 4000,
    ) -> DraftSection:
        from pdd_agent.llm.provider import DraftSection

        prov_str = ", ".join(provenance) if provenance else "none"
        return DraftSection(
            section_id=section_id,
            sub_section_id=sub_section_id,
            text=(
                f"[OLLAMA STUB — {section_id}"
                f"{'.' + sub_section_id if sub_section_id else ''}]\n"
                f"Configure OllamaProvider with a base_url pointing to a local Ollama instance.\n"
                f"Relevant provenance: {prov_str}"
            ),
            confidence="UNSUPPORTED",
            provenance=provenance,
            issues=["REVIEW REQUIRED: Ollama provider not yet configured"],
            provider=self.name,
            output_references=[{"type": "section_body", "description": "ollama stub output"}],
        )

    def close(self) -> None:
        pass
