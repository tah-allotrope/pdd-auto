"""Run survivability: estimates, checkpointing, resume, workers (PHASE-06, S-6).

Uses the ``noop`` provider and ``tmp_path`` for ``runs_dir`` — no network,
no API keys.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import yaml

from pdd_agent.agent.section_orchestrator import SectionOrchestrator
from pdd_agent.llm.budget import estimate_run
from pdd_agent.llm.provider import DraftSection, NoopProvider


def _canonical_ssids() -> list[tuple[str, str]]:
    schema = yaml.safe_load(
        (Path(__file__).parent.parent / "schemas" / "pdd_section_schema.yaml").read_text(
            encoding="utf-8"
        )
    )
    return [
        (sec["section_id"], ss["sub_section_id"])
        for sec in schema["sections"]
        for ss in sec.get("sub_sections", [])
    ]


class TestEstimateRun:
    def test_token_estimate(self):
        estimate = estimate_run(
            {"1.1": 4000, "4.1": 20000},
            avg_prompt_chars=9000,
            model="gpt-4o",
            provider="openai",
        )
        assert estimate["input_tokens"] == 5143  # round(2 * 9000 / 3.5)
        assert estimate["output_tokens"] == 6857  # round((4000 + 20000) / 3.5)
        assert estimate["estimated_cost_usd"] > 0

    def test_overhead_adds_per_section(self):
        plain = estimate_run(
            {"1.1": 4000, "4.1": 20000},
            avg_prompt_chars=9000,
            model="gpt-4o",
            provider="openai",
        )
        overhead = estimate_run(
            {"1.1": 4000, "4.1": 20000},
            avg_prompt_chars=9000,
            model="gpt-4o",
            provider="claude-code",
            overhead_tokens_per_section=25000,
        )
        assert overhead["total_tokens"] - plain["total_tokens"] == 50_000


class TestCheckpointing:
    def test_single_section_checkpoint_on_disk(self, tmp_path: Path):
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            run_id="checkpoint-one",
            runs_dir=tmp_path,
            only_sections=["1.1"],
        )
        orch.draft_all_sections()
        run_file = tmp_path / "checkpoint-one.json"
        assert run_file.exists()
        assert len(json.loads(run_file.read_text(encoding="utf-8"))["sections"]) == 1

    def test_two_sections_checkpoint_on_disk(self, tmp_path: Path):
        orch = SectionOrchestrator(
            provider=NoopProvider(),
            run_id="checkpoint-two",
            runs_dir=tmp_path,
            only_sections=["1.1", "1.2"],
        )
        orch.draft_all_sections()
        assert orch.checkpoint() == tmp_path / "checkpoint-two.json"
        assert (
            len(
                json.loads((tmp_path / "checkpoint-two.json").read_text(encoding="utf-8"))[
                    "sections"
                ]
            )
            == 2
        )


class TestResume:
    def test_real_text_skipped_placeholder_redrafted(self, tmp_path: Path):
        first = SectionOrchestrator(
            provider=NoopProvider(),
            run_id="resume-run",
            runs_dir=tmp_path,
            only_sections=["1.1", "1.2"],
        )
        first.draft_all_sections()
        run_file = tmp_path / "resume-run.json"
        record = json.loads(run_file.read_text(encoding="utf-8"))
        assert len(record["sections"]) == 2
        record["sections"][0]["text"] = "Real authored content for section 1.1."
        run_file.write_text(json.dumps(record), encoding="utf-8")

        resumed = SectionOrchestrator(
            provider=NoopProvider(),
            run_id="resume-run",
            runs_dir=tmp_path,
            only_sections=["1.1", "1.2"],
            resume=True,
        )
        resumed.draft_all_sections()
        assert resumed.drafted_sections["1/1.1"].text == "Real authored content for section 1.1."
        keys = [(s.section_id, s.sub_section_id) for s in resumed.draft_run.sections]
        assert sorted(keys) == [("1", "1.1"), ("1", "1.2")]


class TestWorkers:
    def test_full_schema_in_canonical_order(self, tmp_path: Path):
        orch = SectionOrchestrator(
            provider=NoopProvider(), run_id="workers-run", runs_dir=tmp_path, max_workers=4
        )
        results = orch.draft_all_sections()
        expected = _canonical_ssids()
        assert len(results) == 36
        assert [(s.section_id, s.sub_section_id) for s in orch.draft_run.sections] == expected


class TestStoreDraft:
    def test_redraft_replaces_entry(self, tmp_path: Path):
        orch = SectionOrchestrator(provider=NoopProvider(), runs_dir=tmp_path)

        def _draft(text: str) -> DraftSection:
            return DraftSection(
                section_id="4",
                sub_section_id="4.1",
                text=text,
                confidence="MEDIUM",
                provenance=[],
                issues=[],
                provider="noop",
            )

        orch._store_draft("4/4.1", _draft("first"))
        orch._store_draft("4/4.1", _draft("second"))
        matches = [
            s for s in orch.draft_run.sections if (s.section_id, s.sub_section_id) == ("4", "4.1")
        ]
        assert len(matches) == 1
        assert matches[0].text == "second"


class TestDraftCliEstimateOnly:
    def test_estimate_only_exits_zero(self, capsys):
        from pdd_agent.cli import main

        argv = [
            "pdd-agent",
            "draft",
            "--input",
            "configs/projects/demo_socson_like.yaml",
            "--provider",
            "noop",
            "--estimate-only",
        ]
        with patch.object(sys, "argv", argv):
            assert main() == 0
        assert "estimated_cost_usd" in capsys.readouterr().out
