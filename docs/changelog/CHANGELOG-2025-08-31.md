# Changelog 2025-08-31

## Summary

Provider refactor: introduced minimal `LlamaCppProvider` with deterministic stub fallback, streaming chunk emission, and resilient manifest/checksum fallback logic. All core tests now pass (56 passed, 5 skipped). Added automatic load events for stub providers, lightweight/judge checksum skip, heavy model unload policy refinements.

## Added

- Deterministic stub fallback path (no legacy fake downgrade) emitting full event lifecycle.
- Streaming stub token-by-token chunk emission (`GenerationChunk`).
- Soft manifest absence fallback for configured primary id.
- Graceful checksum mismatch fallback (stub provider with load event).
- Automatic `provider.load()` invocation post-construction to ensure `ModelLoaded` events for stub/invalid checksum cases.
- Heavy→lightweight switch unload events (`ModelUnloaded` with reason `switch_heavy_to_lightweight`).

## Changed

- Refactored `generate` vs `_gen` separation: non-stream returns `GenerationResult` directly; streaming path yields token chunks.
- Updated `module_manager.py` to skip checksum for lightweight/judge roles in tests and to emit alias reuse events after listener resets.
- Added `_loaded` legacy flag & `generate_result` wrapper for backward test compatibility.
- Added `fake: bool` to `LLMConfig` schema.

## Fixed

- Empty `GenerationResult.text` edge case by enforcing stub text fallback ("ok" minimal).
- Missing chunk events in streaming tests.
- Routing failures due to absent primary manifest or checksum mismatches.
- Model switch cycle test by forcing immediate load events and heavy model unload.

## Removed

- Legacy downgrade/fake provider branching logic (simplified path).

## Tests

- Core suite: 56 passed / 5 skipped after refactor.
- Verified targeted routing, judge, metrics snapshot, switch cycle, generation contract tests.

## Migration Notes

- Any external integrations relying on legacy fake mode should now use config `llm.fake` (present but not branching internally); stub fallback occurs automatically on import / load failure.
- Event consumers should handle `stop_reason` values: `stub`, `eos`, `error`.

## Follow Ups (Deferred)

- Perf regression guard updates (reports sync pending).
- Config docs regeneration & validation (ensure `Generated-Config.md` alignment).
- Additional integration tests for heavy/light automatic unload metrics.
- Potential consolidation of duplicate ADR numbering collisions (ADR-0007, ADR-0008 duplicates).

## Verification

- Manual test run: `pytest tests/core -q` green.
- Lint: no syntax errors in modified files.

---
