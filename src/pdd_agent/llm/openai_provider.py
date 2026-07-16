"""OpenAI GPT-4 provider with retry logic, error handling, and token tracking.

Requires: openai>=1.0.0 (install via `pip install pdd-agent[llm]`)
"""

from __future__ import annotations

import time
import structlog

from pdd_agent.llm.budget import BudgetExhaustedError
from pdd_agent.llm.provider import BaseProvider, DraftSection, LLMResponse, ModelConfig

logger = structlog.get_logger()

_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2.0

_DEFAULT_SYSTEM_PROMPT = (
    "You are a technical writing assistant specializing in Verra VCS "
    "carbon credit Project Design Documents for waste-to-energy projects. "
    "Follow the prompt instructions exactly. Cite all sources using the "
    "required citation format. Never fabricate data."
)


class OpenAIProviderError(Exception):
    """Raised when the OpenAI provider encounters a non-retryable error."""


class OpenAIProvider(BaseProvider):
    """OpenAI provider using the chat completions API with structured output."""

    name = "openai"

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._client = None
        self._model = config.model_name or "gpt-4o"
        self._budget = None
        self._system_prompt = _DEFAULT_SYSTEM_PROMPT

    def set_budget(self, budget) -> None:
        """Attach a TokenBudget instance for per-run tracking."""
        self._budget = budget

    def set_system_prompt(self, text: str) -> None:
        """Override the system message used on every subsequent draft call."""
        self._system_prompt = text

    def _get_client(self):
        if self._client is None:
            try:
                import openai
            except ImportError as exc:
                raise OpenAIProviderError(
                    "openai package not installed. Install via: pip install pdd-agent[llm]"
                ) from exc
            if not self._config.api_key:
                raise OpenAIProviderError(
                    "OpenAI API key not configured. Set api_key in ModelConfig."
                )
            kwargs = {"api_key": self._config.api_key}
            if self._config.base_url:
                kwargs["base_url"] = self._config.base_url
            self._client = openai.OpenAI(**kwargs)
        return self._client

    def _call_api(self, prompt: str, max_tokens: int) -> LLMResponse:
        """Call the OpenAI chat completions API with retry logic."""
        import openai

        client = self._get_client()
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": prompt},
        ]

        last_error = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                if self._budget:
                    self._budget.check_budget()

                response = client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=self._config.temperature,
                )
                choice = response.choices[0]
                usage = response.usage

                input_tokens = usage.prompt_tokens if usage else 0
                output_tokens = usage.completion_tokens if usage else 0

                return LLMResponse(
                    text=choice.message.content or "",
                    provider=self.name,
                    model=response.model,
                    tokens_used=(input_tokens + output_tokens) if usage else None,
                    cost_usd=None,
                    raw={
                        "id": response.id,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "finish_reason": choice.finish_reason,
                    },
                )
            except openai.RateLimitError as exc:
                last_error = exc
                wait = _RETRY_BACKOFF_BASE**attempt
                logger.warning(
                    "openai_rate_limit",
                    attempt=attempt,
                    wait_seconds=wait,
                    error=str(exc),
                )
                time.sleep(wait)
            except openai.APITimeoutError as exc:
                last_error = exc
                wait = _RETRY_BACKOFF_BASE**attempt
                logger.warning(
                    "openai_timeout",
                    attempt=attempt,
                    wait_seconds=wait,
                    error=str(exc),
                )
                time.sleep(wait)
            except openai.APIConnectionError as exc:
                last_error = exc
                wait = _RETRY_BACKOFF_BASE**attempt
                logger.warning(
                    "openai_connection_error",
                    attempt=attempt,
                    wait_seconds=wait,
                    error=str(exc),
                )
                time.sleep(wait)
            except openai.AuthenticationError as exc:
                raise OpenAIProviderError(f"OpenAI authentication failed: {exc}") from exc
            except openai.BadRequestError as exc:
                raise OpenAIProviderError(f"OpenAI bad request: {exc}") from exc

        raise OpenAIProviderError(
            f"OpenAI API call failed after {_MAX_RETRIES} retries: {last_error}"
        )

    def draft_section(
        self,
        section_id: str,
        sub_section_id: str,
        prompt: str,
        provenance: list[str],
        max_chars: int = 4000,
    ) -> DraftSection:
        max_tokens = min(self._config.max_tokens, max_chars)

        try:
            response = self._call_api(prompt, max_tokens)
        except (OpenAIProviderError, BudgetExhaustedError) as exc:
            logger.error(
                "openai_draft_failed",
                section_id=section_id,
                sub_section_id=sub_section_id,
                error=str(exc),
            )
            return DraftSection(
                section_id=section_id,
                sub_section_id=sub_section_id,
                text=f"[OPENAI ERROR — {section_id}"
                f"{'.' + sub_section_id if sub_section_id else ''}]\n"
                f"Provider error: {exc}\n"
                f"This section requires manual drafting or retry.",
                confidence="UNSUPPORTED",
                provenance=provenance,
                issues=[f"OPENAI ERROR: {exc}"],
                provider=self.name,
                output_references=[{"type": "section_body", "description": "openai error output"}],
            )

        if self._budget and response.raw:
            self._budget.record(
                section_id=f"{section_id}.{sub_section_id}" if sub_section_id else section_id,
                input_tokens=response.raw.get("input_tokens", 0),
                output_tokens=response.raw.get("output_tokens", 0),
                model=response.model or self._model,
            )

        text = response.text[:max_chars]
        confidence = self._assess_confidence(text, provenance)

        return DraftSection(
            section_id=section_id,
            sub_section_id=sub_section_id,
            text=text,
            confidence=confidence,
            provenance=provenance,
            issues=self._extract_issues(text, section_id, sub_section_id),
            provider=self.name,
            output_references=[{"type": "section_body", "description": "openai generated output"}],
        )

    def _assess_confidence(self, text: str, provenance: list[str]) -> str:
        has_review_markers = "[REVIEW REQUIRED" in text or "[MISSING]" in text
        has_inference = "[INFERENCE]" in text
        has_citations = any(
            marker in text for marker in ("[CORPUS:", "[METHODOLOGY:", "[E0", "[USER INPUT:")
        )

        if has_review_markers and not has_citations:
            return "LOW"
        if has_review_markers or has_inference:
            return "MEDIUM"
        if has_citations and provenance:
            return "HIGH"
        return "MEDIUM"

    def _extract_issues(self, text: str, section_id: str, sub_section_id: str) -> list[str]:
        issues = []
        if "[REVIEW REQUIRED" in text:
            issues.append(
                f"Contains [REVIEW REQUIRED] markers in {section_id}"
                f"{'.' + sub_section_id if sub_section_id else ''}"
            )
        if "[MISSING]" in text:
            issues.append(
                f"Contains [MISSING] markers — evidence gaps in {section_id}"
                f"{'.' + sub_section_id if sub_section_id else ''}"
            )
        if "[INFERENCE]" in text:
            issues.append(
                f"Contains [INFERENCE] markers — model-inferred content in {section_id}"
                f"{'.' + sub_section_id if sub_section_id else ''}"
            )
        return issues

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
