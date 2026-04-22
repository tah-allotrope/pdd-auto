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
