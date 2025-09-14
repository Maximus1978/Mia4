# 2025-08-29 – Harmony Postproc Stage 1

## Added
- Harmony tag mode (buffered) `<analysis>/<final>` with fallback to marker.
- Refactored `core/llm/postproc.py` (unified marker + harmony paths).
- Config keys `llm.prompt.harmony.*` documented and enforced.
- README, API, Config-Registry, model passport updated.
- ADR-0014 updated (Accepted + Harmony section).
- State snapshot `STATE_SNAPSHOT_2025-08-29.md` created.

## Changed
- Marker mode: now suppresses `reasoning_text` in final event when `drop_from_history=true` (explicit).

## Tests
- Added harmony tests: split + fallback.
- Regenerated & validated postproc regression tests (marker split, truncation, ngram, suppression).

## Deferred
- Incremental harmony streaming & analysis SSE channel.
- Mismatch metric & alerting.
- Consistent `drop_from_history` semantics across harmony.

## Notes
No breaking changes; marker mode behavior for clients unchanged except explicit omission of reasoning_text (already expected by UI).
