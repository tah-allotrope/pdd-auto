# Provider Scorecard — Key-Gated Live-Run Checklist

**Status:** Ready to execute. Blocked only on `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` being available in the environment (ASM-001 of `plans/2026-07-12-pdd-reality-gap-plan.md`).

This is TASK-04-06 of PHASE-04. All code is implemented and unit-tested with mocks (`tests/test_provider_scorecard.py`, `tests/test_judge.py`); the command below is a copy-paste exercise once keys land.

## Steps

1. Set the keys and a cost ceiling:
   ```bash
   export OPENAI_API_KEY=sk-...
   export ANTHROPIC_API_KEY=sk-ant-...
   export PDD_MAX_COST_USD=20
   ```
   (Or place them in a `.env` file at the repo root — loaded automatically since PHASE-01.)

2. Run the three-provider scorecard on the Inegol project:
   ```bash
   pdd-agent scorecard \
     --input configs/demo/inegol_project_input.yaml \
     --providers ollama,openai,anthropic \
     --output reports/provider-scorecard.md
   ```
   Ollama requires a local instance reachable at `OLLAMA_BASE_URL` (default `http://localhost:11434`) with a model pulled — see `docs/2026-07-12-ollama-shakeout.md` for setup and this environment's hardware caveat (CPU-only local inference may not complete within the 120s per-attempt timeout; OpenAI/Anthropic have no such constraint).

3. Review `reports/provider-scorecard.md`: compare sections drafted, judge pass rate, mean judge score, redraft count, total tokens, estimated cost, and wall-clock time per provider.

4. Pick the default drafting model based on the scorecard (DEC-001: dual-provider benchmarking picks the default; Ollama is a dev/shakeout tier, not a quality tier).

5. Export the winning provider's run:
   ```bash
   pdd-agent export --run-id <run-id-of-winning-provider>
   ```

6. Hand the exported DOCX to the domain expert (user or Tinh) for VVB-desk-review-grade sign-off, per DEC-002 from `research/2026-07-05_pdd-next-level-brainstorm.md`: "a domain expert judges submittable to a VVB with minor edits."

7. Record the outcome — which provider/model won, the domain expert's verdict, and the date — in a new `docs/YYYY-MM-DD-provider-scorecard-results.md`.

## What's already verified without keys

- `pdd-agent scorecard --input configs/demo/inegol_project_input.yaml --providers demo --output <path>` completes and renders a valid 8-column markdown table (verified 2026-07-12, see `reports/` for prior test runs).
- A provider requested without its API key (e.g. `openai` with no `OPENAI_API_KEY`) is skipped with a logged warning and a "skipped: missing_api_key" row — the scorecard never crashes on a misconfigured provider list.
- The LLM-judge's structured JSON findings parser (`_parse_judge_json`) is unit-tested against clean JSON, markdown-fenced JSON, and unparseable text (falls back to deterministic scoring).
- Judge model tiers resolve correctly: `PDD_JUDGE_MODEL` env override, then per-provider tier defaults (`claude-haiku-4-5-20251001` for Anthropic, `gpt-4o-mini` for OpenAI), then explicit constructor arg takes top priority.
