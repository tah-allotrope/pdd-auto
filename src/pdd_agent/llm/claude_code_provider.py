"""Claude Code CLI provider — keyless frontier drafting via the local CLI.

Shells out to the headless one-shot mode of the installed ``claude`` CLI
(``claude -p --output-format json --model {model} --append-system-prompt
"{system_prompt}"``, prompt piped via stdin) instead of requiring an API
key, so drafting can use a frontier Anthropic model through the operator's
Claude subscription with zero API key configured. No ``anthropic`` pip
package or ``ANTHROPIC_API_KEY`` needed — mirrors ``ollama_provider.py``'s
retry, marker-detection, and confidence-assignment structure.

CLI contract verified 2026-07-17 against Claude Code CLI 2.1.211
(``claude --version``) via a live
``echo "..." | claude -p --output-format json --model haiku`` call:

- ``-p``/``--print``, ``--output-format json``, ``--model <alias-or-full-name>``
  (accepts aliases like ``"sonnet"``, ``"haiku"``, ``"opus"``), and
  ``--append-system-prompt <text>`` all exist and behave as documented.
- JSON result shape: a single object with ``result`` (str, completion
  text), ``is_error`` (bool), ``usage.input_tokens`` (int),
  ``usage.output_tokens`` (int), and ``total_cost_usd`` (float — not used
  here, since usage is billed via the operator's subscription, not a
  per-token API rate; see ``configs/model_pricing.yaml``'s ``claude-code``
  entry).
- Parsed defensively regardless: missing ``usage`` fields default to 0;
  a missing/empty ``result`` with ``is_error: false`` is treated as an
  error and retried like any other failure mode.

Install: the Claude Code CLI (``claude``) must be on PATH and
authenticated (an active login session / subscription). Configure via
``configure_provider_from_env("claude-code")``
(``pdd_agent.llm.env_config``) or directly with a ``ModelConfig``.
"""

from __future__ import annotations

import json
import os
import subprocess
import time

import structlog

from pdd_agent.llm.budget import BudgetExhaustedError
from pdd_agent.llm.provider import BaseProvider, DraftSection, LLMResponse, ModelConfig

logger = structlog.get_logger()

_MAX_RETRIES = 2
_RETRY_BACKOFF_BASE = 2.0
_DEFAULT_TIMEOUT_SECONDS = 300
_DEFAULT_MODEL = "sonnet"
_DEFAULT_CLI = "claude"

_DEFAULT_SYSTEM_PROMPT = (
    "You are a technical writing assistant specializing in Verra VCS "
    "carbon credit Project Design Documents for waste-to-energy projects. "
    "Follow the prompt instructions exactly. Cite all sources using the "
    "required citation format. Never fabricate data."
)


class ClaudeCodeProviderError(Exception):
    """Raised when the Claude Code CLI provider encounters a non-retryable error."""


class ClaudeCodeProvider(BaseProvider):
    """Frontier-model provider using the local Claude Code CLI (no API key)."""

    name = "claude-code"

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._model = config.model_name or _DEFAULT_MODEL
        self._cli = os.environ.get("CLAUDE_CODE_CLI", _DEFAULT_CLI)
        self._timeout_seconds = int(
            os.environ.get("CLAUDE_CODE_TIMEOUT_SECONDS", str(_DEFAULT_TIMEOUT_SECONDS))
        )
        self._budget = None
        self._system_prompt = _DEFAULT_SYSTEM_PROMPT

    def set_budget(self, budget) -> None:
        """Attach a TokenBudget instance for per-run tracking."""
        self._budget = budget

    def set_system_prompt(self, text: str) -> None:
        """Override the system message appended via --append-system-prompt."""
        self._system_prompt = text

    def _call_cli(self, prompt: str) -> LLMResponse:
        """Invoke the Claude Code CLI in headless one-shot mode with retry logic."""
        argv = [
            self._cli,
            "-p",
            "--output-format",
            "json",
            "--model",
            self._model,
            "--append-system-prompt",
            self._system_prompt,
        ]

        last_error: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                if self._budget:
                    self._budget.check_budget()

                proc = subprocess.run(
                    argv,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=self._timeout_seconds,
                )
                if proc.returncode != 0:
                    raise ClaudeCodeProviderError(
                        f"claude CLI exited {proc.returncode}: {proc.stderr.strip()[:500]}"
                    )

                payload = json.loads(proc.stdout)
                if payload.get("is_error"):
                    raise ClaudeCodeProviderError(
                        f"claude CLI reported is_error=true: {proc.stdout[:500]}"
                    )
                text = payload.get("result") or ""
                if not text:
                    raise ClaudeCodeProviderError(
                        f"claude CLI returned no result text: {proc.stdout[:500]}"
                    )

                usage = payload.get("usage") or {}
                input_tokens = usage.get("input_tokens", 0) or 0
                output_tokens = usage.get("output_tokens", 0) or 0

                return LLMResponse(
                    text=text,
                    provider=self.name,
                    model=self._model,
                    tokens_used=input_tokens + output_tokens,
                    cost_usd=0.0,
                    raw={
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    },
                )
            except BudgetExhaustedError:
                raise
            except ClaudeCodeProviderError as exc:
                last_error = exc
                logger.warning("claude_code_call_failed", attempt=attempt, error=str(exc))
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_BACKOFF_BASE**attempt)
            except subprocess.TimeoutExpired as exc:
                last_error = exc
                logger.warning("claude_code_timeout", attempt=attempt, error=str(exc))
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_BACKOFF_BASE**attempt)
            except (json.JSONDecodeError, OSError) as exc:
                last_error = exc
                logger.warning("claude_code_bad_response", attempt=attempt, error=str(exc))
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_BACKOFF_BASE**attempt)

        raise ClaudeCodeProviderError(
            f"claude CLI call failed after {_MAX_RETRIES} retries: {last_error}"
        )

    def draft_section(
        self,
        section_id: str,
        sub_section_id: str,
        prompt: str,
        provenance: list[str],
        max_chars: int = 4000,
    ) -> DraftSection:
        try:
            response = self._call_cli(prompt)
        except (ClaudeCodeProviderError, BudgetExhaustedError) as exc:
            logger.error(
                "claude_code_draft_failed",
                section_id=section_id,
                sub_section_id=sub_section_id,
                error=str(exc),
            )
            return DraftSection(
                section_id=section_id,
                sub_section_id=sub_section_id,
                text=f"[CLAUDE-CODE ERROR — {section_id}"
                f"{'.' + sub_section_id if sub_section_id else ''}]\n"
                f"Provider error: {exc}\n"
                f"This section requires manual drafting or retry. Is the "
                f"`claude` CLI installed and authenticated?",
                confidence="UNSUPPORTED",
                provenance=provenance,
                issues=[f"CLAUDE-CODE ERROR: {exc}"],
                provider=self.name,
                output_references=[
                    {"type": "section_body", "description": "claude-code error output"}
                ],
            )

        if self._budget and response.raw:
            self._budget.record(
                section_id=f"{section_id}.{sub_section_id}" if sub_section_id else section_id,
                input_tokens=response.raw.get("input_tokens", 0),
                output_tokens=response.raw.get("output_tokens", 0),
                model=response.model or self._model,
                provider=self.name,
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
            output_references=[
                {"type": "section_body", "description": "claude-code generated output"}
            ],
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
        pass
