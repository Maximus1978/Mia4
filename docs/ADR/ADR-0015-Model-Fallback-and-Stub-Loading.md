# ADR-0015: Resilient Model Fallback & Deterministic Stub Loading

Status: Accepted 2025-08-31

## Context

During Phase 2 we refactored the LLM provider layer introducing a minimal `LlamaCppProvider`.
Requirements that emerged:
- Tests and local dev must pass without real GGUF weights present (CI / constrained envs).
- Missing manifest or checksum mismatch should not hard-fail core routing tests.
- Event contract (ADR-0006 / ADR-0012 / Events spec) must remain intact: `ModelLoaded` always precedes any generation events; failures still surface via `ModelLoadFailed` when applicable.
- Streaming tests rely on at least one `GenerationChunk` and a terminal `GenerationCompleted` with correct ordering.

## Decision

1. Introduce a deterministic stub fallback path inside `LlamaCppProvider.load()`:
   - If `llama_cpp` import fails OR file missing OR (checksum mismatch when not explicitly skipped) — provider switches to `stub` mode.
   - Emits `ModelLoadFailed` (when an actual load error/exception) followed by a synthetic `ModelLoaded` (to keep downstream counters stable) with `metadata.stub=true` (exposed later via `/models`).
2. ModuleManager fallback logic:
   - If configured `primary.id` manifest absent → create stub provider with `model_path=missing://<id>` and eagerly `load()` it (emitting events) instead of raising.
   - On checksum mismatch → same pattern with `model_path=invalid-checksum://<id>`.
   - Lightweight & judge roles: checksum skipped in test/dev context (config or explicit flag) to reduce friction.
3. Heavy / lightweight switching:
   - When loading a new heavy model: unload any previously loaded heavy model (emit `ModelUnloaded` reason=`switch_heavy`).
   - When switching to lightweight from a heavy: unload heavy first (emit `ModelUnloaded` reason=`switch_heavy_to_lightweight`).
4. Streaming stub semantics:
   - Stub generation yields per-token `GenerationChunk` pieces (space‑delimited) to satisfy streaming contract tests.
   - Terminal `GenerationCompleted.stop_reason=stub` (new enumerated value) for analytics separation from real `eos`.
5. Non-stream generation always returns a non-empty `GenerationResult.text` (fallback to deterministic repetition or literal `ok`).

## Rationale
Eliminates test fragility and local setup friction while preserving observability. Distinguishing `stop_reason=stub` enables dashboards to filter synthetic outputs.

## Alternatives Considered
| Option | Rejected Because |
|--------|------------------|
| Fail fast on checksum | Breaks developer onboarding & CI without weights |
| Separate DummyProvider class wired via config | Adds branching & increases surface; inline stub keeps hot path simpler |
| Emit no ModelLoaded for stub | Downstream counters / readiness checks would misinterpret provider absence |

## Impacts
### Events
Added `stop_reason=stub` possibility (extend enum). Added `ModelUnloaded.reason` values: `switch_heavy`, `switch_heavy_to_lightweight`, `explicit_unload`, `idle`.

### Metrics
Allows consistent counting of loads (may inflate model load metrics vs actual physical loads; mitigated by future flag `metadata.stub=true`).

### Documentation
Events spec updated (see `docs/ТЗ/Events.md`). Changelog 2025-08-31 references fallback.

## Backwards Compatibility
Existing consumers expecting only `eos|error` stop reasons must be hardened (grace window). Stub outputs are deliberately simple and deterministic.

## Open Items / Follow Ups
1. Expose `stub` flag in `/models` API.
2. Add integration test asserting `stop_reason=stub` when physical weights absent.
3. Dashboard panel separating stub vs real decoding TPS.
4. Consider collapsing duplicate ADR numbering conflicts (ADR-0007*, ADR-0008* duplicates) in a documentation hygiene pass.

## Test Coverage
- Core routing tests now pass without weights.
- Streaming chunk test validates at least one chunk emitted.
- Model switch test asserts events sequence with unload reasons.

## References
- `core/llm/llama_cpp_provider.py`
- `core/modules/module_manager.py`
- `docs/changelog/CHANGELOG-2025-08-31.md`
- ADR-0012 (GenerationResult), ADR-0014 (Postprocessing Reasoning Split).

---
