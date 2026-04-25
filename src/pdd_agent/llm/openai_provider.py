"""OpenAI structured-output provider stub.

Wire this in by calling configure_provider() with a ModelConfig
where provider_name="openai" and api_key is set.
Requires: openai>=1.0.0
"""

from __future__ import annotations

from pdd_agent.llm.provider import BaseProvider, DraftSection, ModelConfig


class OpenAIProvider(BaseProvider):
    """OpenAI provider using structured output via the responses API."""

    name = "openai"

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._client = None

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
                f"[OPENAI STUB — {section_id}"
                f"{'.' + sub_section_id if sub_section_id else ''}]\n"
                f"Configure OpenAIProvider with a valid API key to generate real content.\n"
                f"Relevant provenance: {prov_str}"
            ),
            confidence="UNSUPPORTED",
            provenance=provenance,
            issues=["REVIEW REQUIRED: OpenAI provider not yet configured"],
            provider=self.name,
            output_references=[{"type": "section_body", "description": "openai stub output"}],
        )

    def close(self) -> None:
        if self._client:
            self._client.close()
