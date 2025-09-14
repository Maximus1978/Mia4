# ADR-0026: Model Pipeline Separation & Routing Layer

Status: Proposed
Date: 2025-09-03
Authors: Core Team
Supersedes: —
Relates-To: ADR-0015 (Fallback), ADR-0016 (Passports), ADR-0021 (Cap Observability)

## Context

Current `generate` endpoint in `mia4.api.routes.generate` inlines multiple responsibilities:

- Merge sampling layers (passport, preset, user overrides)
- Build Harmony system+developer+user prompt
- Apply reasoning preset & postproc adjustments
- Enforce caps (max_output_tokens) & produce observability events
- Select & drive streaming adapter (HarmonyChannelAdapter)
- Postprocess final text & emit usage/final events

This monolithic flow couples provider-specific behavior (primary gpt-oss path) with generic request handling. Introduction of additional model roles ("lightweight", future "rag", "json-mode" etc.) and policy-driven routing (fallback, heuristic trigger) requires isolation of per-model pipelines.

## Decision

Introduce an explicit Model Pipeline abstraction decoupling request lifecycle phases from the HTTP route. Each model role is backed by a `GenerationPipeline` implementation with uniform contract:

```python
class GenerationPipeline(ABC):
   def prepare(self, req: GenerateRequest, provider, config) -> PipelineContext: ...
   def stream(self, ctx: PipelineContext) -> Iterable[SSEPayload]: ...
   def finalize(self, ctx: PipelineContext) -> PipelineResult: ...
```

Routing layer resolves `(provider, pipeline_class)` given `model_id` (and future policies). `generate()` orchestrates only high-level control: build context via `prepare`, relay SSE from `stream`, then `finalize` to emit completion events.

## Goals

- Independent evolution of primary vs lightweight (or future specialized) pipelines
- Clear insertion points for: RAG augmentation, tool calling enrichments, fallback triggers, adaptive sampling
- Simplified testing: unit-test pipeline classes in isolation
- Observability parity: sampling & cap metadata emitted coherently across pipelines

## Non-Goals (this ADR)

- Implement heuristic / dynamic routing decisions
- Implement multi-pass fallback execution
- Extend lightweight pipeline behavior beyond stub

## Pipeline Phases

1. prepare():
   - Normalize & validate overrides
   - Merge sampling layers (passport/preset/user)
   - Compute caps (passport + primary) -> (requested, effective, cap_applied, source)
   - Construct prompt (Harmony framing) and adapter selection metadata
   - Emit `GenerationStarted`

2. stream():
   - Drive provider.stream with adapter
   - Surface channel events (analysis/commentary/final) as SSE payloads
   - Track reasoning stats & latency metrics

3. finalize():
   - Assemble final text, apply post-processing (echo stripping, stop sequence handling)
   - Emit `GenerationCompleted` (or `GenerationCancelled` from route on abort/timeout)
   - Return structured result (including sampling & reasoning stats) for route to send final SSE blocks

## Routing Layer

`core/llm/router.py`:

```python
class ModelRouter:
   def resolve(self, model_id: str) -> tuple[Provider, type[GenerationPipeline]]
```
Initial mapping: primary id -> PrimaryPipeline; (if lightweight configured) -> LightweightPipeline; else error if unknown.

Emit new event `ModelRouted`:

```text
ModelRouted { request_id, model_id, pipeline: "primary"|"lightweight"|..., capabilities: { tool_calls: bool, reasoning_split: bool } }
```

## Data Structures

- `PipelineContext`: dataclass capturing request_id, prompt, sampling (requested/effective/cap flags), adapter, timing, fragments, reasoning_stats.
- `PipelineResult`: final_text, usage_stats, reasoning_stats, sampling_summary.

## Observability Invariants

- Sampling snapshot appears in `GenerationStarted.sampling` (already) and `GenerationCompleted.result_summary.sampling`.
- `cap_applied` + `cap_source` stable across start/finish.
- Channel token metrics remain adapter-owned (no change).

## Migration Plan

1. Extract helper pure functions from current route: prompt build, sampling merge, cap enforcement.
2. Implement `PrimaryPipeline` reusing extracted logic (no behavior change).
3. Add router + ModelRouted event (synchronous emit after prepare()).
4. Refactor route to use router/pipeline.
5. Add stub `LightweightPipeline` returning NotImplemented for prepare() if invoked (guarded by config absence) – ensures independence without feature creep.
6. Tests:
   - test_primary_pipeline_separation (ensures route uses pipeline & events fired)
   - adapt existing cap test (no change expected) still green
   - stub test ensuring absence of lightweight config does not raise.

## Risks & Mitigations

- Risk: Hidden coupling in current route logic -> Mitigate via incremental extraction + snapshot tests.
- Risk: Event contract drift -> Add test asserting sampling fields equality between Started and Completed.
- Risk: Performance regression (extra abstraction) -> Minimal overhead; verify decode_tps unchanged within tolerance.

## Alternatives Considered

- Keep monolithic function and feature-flag new pipelines: increases future refactor cost, harder to test.
- Strategy pattern directly inside route without separate module: still clutters route; discourages reuse.

## Future Extensions

- Policy engine for dynamic routing (latency / cost heuristic)
- Fallback chain execution (see ADR-0015)
- Capability negotiation (e.g., tool calling enablement)
- RAG pipeline injecting retrieved context in prepare()

## Conclusion

Separation provides a clean scaffold for upcoming routing, RAG, and adaptive behaviors with minimal immediate complexity. Proceed with implementation per migration plan.
