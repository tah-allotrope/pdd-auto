# Methodology data refresh

The files in this directory are curated snapshots, not live registry results.

1. Download the current active methodology lists from the official Verra VCS and UNFCCC CDM sources.
2. Update `verra_vcs_active.json` and `cdm_active.json` without changing the documented schema.
3. Set `_meta.last_updated` to the source publication or retrieval date and record the source URL in `_meta.source`.
4. Preserve stable methodology IDs, remove inactive entries, and deduplicate IDs across both files.
5. Run `python -m pytest tests/test_methodology_screen.py -q` and manually verify representative WTE and non-WTE rankings.

LLM analysis may re-rank only methodologies present in these active snapshots. It is not an authority for active status.
