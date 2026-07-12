# Corpus Readiness Report — VERRA WTE Bucket
**Generated:** 2026-04-22 09:27 UTC
**Source folder:** `1pp23yRZ8qtopw1BPXrzVewXsmmWplCse` (VERRA)

## Summary

| Metric | Value |
| --- | --- |
| Total files inventoried | 13 |
| Parseable (PDF/DOCX) | 13 |
| In initial bucket | 13 |
| Out of bucket | 0 |
| Needs manual review | 0 |
| Total words (normalized) | 419,799 |
| Total pages extracted | 0 |

## MIME Type Distribution

- `application/pdf`: 13

## Per-File Detail

| File | MIME | Bucket | Words | Headings | Parseable |
| --- | --- | --- | ---: | ---: | ---: |
| VCS_Bergama_Project-Description.pdf | application/pdf | `IN_BUCKET` | 51,762 | 361 | YES |
| VCS_DRAFT_Yanjiang_Project-Description.pdf | application/pdf | `IN_BUCKET` | 28,660 | 200 | YES |
| VCS_Guangzhou_Project-Description.pdf | application/pdf | `IN_BUCKET` | 31,792 | 174 | YES |
| VCS_Guanxi Zhuang_Project_Description.pdf | application/pdf | `IN_BUCKET` | 26,784 | 147 | YES |
| VCS_Inegol_Project-Description.pdf | application/pdf | `IN_BUCKET` | 37,855 | 215 | YES |
| VCS_Linfen_Project-Description.pdf | application/pdf | `IN_BUCKET` | 33,739 | 194 | YES |
| VCS_Lizuhou_Project-Description.pdf | application/pdf | `IN_BUCKET` | 41,361 | 223 | YES |
| VCS_Mahindra_Project-Description.pdf | application/pdf | `IN_BUCKET` | 16,213 | 161 | YES |
| VCS_Shunping_Project-Description.pdf | application/pdf | `IN_BUCKET` | 43,294 | 272 | YES |
| VCS_Soc Son_Project-Description.pdf | application/pdf | `IN_BUCKET` | 27,412 | 190 | YES |
| VCS_Tamil Nadu_Project-Description.pdf | application/pdf | `IN_BUCKET` | 19,281 | 168 | YES |
| VCS_Yingoku_Project-Description.pdf | application/pdf | `IN_BUCKET` | 22,741 | 123 | YES |
| VCS_Ã–demis_Project-Description.pdf | application/pdf | `IN_BUCKET` | 38,905 | 278 | YES |

## Bucket Configuration

- **Config file:** `configs\corpus_buckets\verra-wte-initial.yaml`
- **Bucket name:** `verra-wte-initial`
- **Description:** Initial homogeneous bucket: Verra-style waste-to-energy PDDs from the shared VERRA Drive folder, covering MSW, WTE, AD, RDF, and landfill-diversion project types. Excludes non-WTE and non-Verra standards.

## Next Steps

1. **Review NEEDS_REVIEW files** — manually inspect files flagged NEEDS_REVIEW and either move them out of the Drive folder or lower the inclusion threshold in the bucket config.
2. **Confirm reference materials** — download official Verra template and methodology documents into `data/reference/verra/` and `data/reference/methodologies/`.
3. **Validate parseability** — for any file flagged NOT parseable, check whether it is a scanned PDF requiring OCR.
4. **Lock bucket before PHASE-02** — once the in-bucket set is stable, update `configs/corpus_buckets/verra-wte-initial.yaml` and commit the manifest.

## New Family Corpora — Registry Fetch Status (2026-07-12)

Per `plans/2026-07-12-pdd-reality-gap-plan.md` PHASE-05, `pdd-agent fetch-registry` was run live against the public Verra registry for the three new methodology families. Bucket configs (`configs/corpus_buckets/verra-{rice-vm0051,biochar-vm0044,cookstove-amsiig}.yaml`) are in place; corpus population is blocked on the registry's exact search API shape.

| Methodology | Command run | Result | Documents downloaded |
|---|---|---|---|
| VM0051 (rice) | `pdd-agent fetch-registry --methodology VM0051 --limit 3 --output-dir data/corpus/registry/vm0051` | Manual-download mode | 0 |
| VM0044 (biochar) | `pdd-agent fetch-registry --methodology VM0044 --limit 3 --output-dir data/corpus/registry/vm0044` | Manual-download mode | 0 |
| AMS-II.G (cookstoves) | `pdd-agent fetch-registry --methodology AMS-II.G --limit 3 --output-dir data/corpus/registry/amsiig` | Manual-download mode | 0 |

**Why manual mode:** the registry search endpoint (`POST https://registry.verra.org/uiapi/asset/asset/search`, confirmed live and reachable) requires an exact OData request shape (`$filter`/`$top`/`$skip` plus specific field names) that could not be fully reconstructed from the minified Angular bundle alone — full reconstruction needs browser devtools network inspection of a real search interaction, which was not available in this environment. See the `download_registered_pdds()` module docstring in `src/pdd_agent/ingest/registry_download.py` for the exact verification evidence (endpoint reachability, `basePath` confirmation, a 406 response to a malformed request proving the endpoint validates input).

**This is a designed, first-class outcome, not a failure** — `manifest.json` in each output directory documents the manual-download instructions. Each family's corpus can be populated by placing PDDs downloaded by hand from https://registry.verra.org/app/search/VCS into the corresponding `data/corpus/registry/<family>/` directory, then calling `refresh_manifest(output_dir)`.

**Next step to unblock:** either (a) inspect the registry's real search XHR payload via browser devtools once available and update `_search_projects()`'s request body to match, or (b) proceed directly to manual downloads — filtering the registry UI by methodology and saving PDD PDFs by hand is a bounded, one-time task per family (~10 documents each).
