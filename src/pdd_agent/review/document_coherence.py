"""Document-level coherence checks over an assembled run record."""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any

import yaml


def _valid_subsection_ids(schema_path: Path | None = None) -> set[str]:
    if schema_path is None:
        schema_path = (
            Path(__file__).parent.parent.parent.parent / "schemas" / "pdd_section_schema.yaml"
        )
    try:
        data = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    ids: set[str] = set()
    for sec in data.get("sections", []):
        for ss in sec.get("sub_sections", []):
            ssid = ss.get("sub_section_id")
            if ssid:
                ids.add(str(ssid))
    return ids


def check_document_coherence(
    run_data: dict[str, Any], schema_path: Path | None = None
) -> list[dict[str, Any]]:
    """Return findings over run_data. Each finding has check, severity, sections, detail."""
    findings: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = (
        run_data.get("sections", []) if isinstance(run_data, dict) else []
    )

    # Title echo
    try:
        schema = yaml.safe_load(
            (
                schema_path
                or Path(__file__).parent.parent.parent.parent
                / "schemas"
                / "pdd_section_schema.yaml"
            ).read_text(encoding="utf-8")
        )
        heading_by_ssid: dict[str, str] = {}
        for sec in schema.get("sections", []):
            for ss in sec.get("sub_sections", []):
                heading_by_ssid[str(ss.get("sub_section_id"))] = str(ss.get("heading", ""))
    except Exception:
        heading_by_ssid = {}

    # Duplicate bodies and cross refs
    # NUMBER_DISAGREEMENT
    # Extract tCO2e numbers
    tco2_pattern = re.compile(r"([\d,]+\.?\d*)\s*(?:tCO2e|tCO2-e|tCO2)", re.IGNORECASE)
    # For NUMBER_DISAGREEMENT: collect all numbers across sections, within 30 chars of tCO2e already captured
    # Use tco2_pattern already ensures number adjacent to unit within few chars
    # Instead group by context? Plan says for each distinct quantity expressed in tCO2e that appears in two or more sections, flag when largest and smallest differ by >1% of largest.
    # Simplistic: collect all tCO2e numbers across sections, if same order of magnitude? We'll group all together if more than one section contains tCO2e numbers.
    # Better: collect per-section list, then global pool
    number_entries: list[tuple[str, float]] = []
    for sec in sections:
        ssid = sec.get("sub_section_id") or sec.get("section_id", "")
        text = sec.get("text", "") or ""
        for m in tco2_pattern.finditer(text):
            raw = m.group(1).replace(",", "")
            try:
                val = float(raw)
            except:  # noqa: E722
                continue
            if val == 0:
                continue
            number_entries.append((ssid, val))

    if len(number_entries) >= 2:
        # Use set of sections
        vals = [v for _, v in number_entries]
        mn = min(vals)
        mx = max(vals)
        if mx > 0 and (mx - mn) / mx > 0.01:
            # flag only if numbers appear in >=2 sections
            distinct_sections = sorted({s for s, _ in number_entries})
            if len(distinct_sections) >= 2:
                findings.append(
                    {
                        "check": "NUMBER_DISAGREEMENT",
                        "severity": "HIGH",
                        "sections": distinct_sections,
                        "detail": f"tCO2e numbers range {mn:,.0f} to {mx:,.0f} differs by >1% of largest",
                    }
                )

    # CALC_DISAGREEMENT — flag any tCO2e number near baseline/project/net words that differs >5% from calc_result
    calc = run_data.get("calc_result") if isinstance(run_data, dict) else None
    if calc and isinstance(calc, dict):
        baseline_val = calc.get("baseline_emissions_tco2e") or calc.get("baseline_total")
        project_val = calc.get("project_emissions_tco2e") or calc.get("project_total")
        net_val = calc.get("net_emission_reductions_tco2e") or calc.get("net_ER")

        # Build normalized calc values list
        for sec in sections:
            ssid = sec.get("sub_section_id") or sec.get("section_id", "")
            text = sec.get("text", "") or ""
            # find numbers with surrounding words
            for m in tco2_pattern.finditer(text):
                raw = m.group(1).replace(",", "")
                try:
                    val = float(raw)
                except:  # noqa: E722
                    continue
                if val == 0:
                    continue
                start = max(0, m.start() - 30)
                end = min(len(text), m.end() + 30)
                snippet = text[start:end].lower()
                target_val = None
                if "baseline" in snippet:
                    target_val = baseline_val
                elif "project emissions" in snippet or "project" in snippet:
                    target_val = project_val
                elif "net" in snippet:
                    target_val = net_val
                else:
                    continue
                if target_val and target_val != 0:
                    rel = abs(val - target_val) / abs(target_val)
                    if rel > 0.05:
                        findings.append(
                            {
                                "check": "CALC_DISAGREEMENT",
                                "severity": "HIGH",
                                "sections": [ssid],
                                "detail": f"section tCO2e {val:,.0f} differs >5% from calc {target_val:,.0f} near '{snippet.strip()[:60]}'",
                            }
                        )
                        break  # one per section

    # DUPLICATE_BODY
    for i in range(len(sections)):
        for j in range(i + 1, len(sections)):
            a = sections[i]
            b = sections[j]
            ta = (a.get("text") or "").lower()
            tb = (b.get("text") or "").lower()
            ta = re.sub(r"\s+", " ", ta.strip())
            tb = re.sub(r"\s+", " ", tb.strip())
            if not ta or not tb:
                continue
            ratio = difflib.SequenceMatcher(None, ta, tb).ratio()
            if ratio >= 0.90:
                findings.append(
                    {
                        "check": "DUPLICATE_BODY",
                        "severity": "ADVISORY",
                        "sections": [
                            a.get("sub_section_id") or a.get("section_id", ""),
                            b.get("sub_section_id") or b.get("section_id", ""),
                        ],
                        "detail": f"sections have near-identical bodies (ratio {ratio:.2f})",
                    }
                )

    # DANGLING_CROSS_REFERENCE
    valid_ids = _valid_subsection_ids(schema_path)
    cross_re = re.compile(r"Section\s+(\d+\.\d+)", re.IGNORECASE)
    for sec in sections:
        ssid = sec.get("sub_section_id") or sec.get("section_id", "")
        text = sec.get("text", "") or ""
        for m in cross_re.finditer(text):
            ref = m.group(1)
            if ref not in valid_ids:
                findings.append(
                    {
                        "check": "DANGLING_CROSS_REFERENCE",
                        "severity": "ADVISORY",
                        "sections": [ssid],
                        "detail": f"reference to Section {ref} not in schema",
                    }
                )
                break

    # TITLE_ECHO
    for sec in sections:
        ssid = sec.get("sub_section_id") or ""
        heading = heading_by_ssid.get(ssid, "")
        text = sec.get("text", "") or ""
        if heading and text:
            # first non-blank line is ATX heading echoing?
            lines = text.splitlines()
            first = None
            for ln in lines:
                if ln.strip():
                    first = ln
                    break
            if first and first.lstrip().startswith("#"):
                # use assembly helper predicate
                from pdd_agent.export.assembly import is_title_echo

                if is_title_echo(first, heading):
                    findings.append(
                        {
                            "check": "TITLE_ECHO",
                            "severity": "ADVISORY",
                            "sections": [ssid],
                            "detail": f"section body starts with heading echoing canonical title '{heading}'",
                        }
                    )

    return findings
