# ADR-0020: Harmony Streaming Migration Plan (Channels-Based Reasoning Split)

Status: Accepted
Date: 2025-09-01
Authors: MIA Core
Related: ADR-0014 (Post-processing Split), ADR-0016 (Passports & Sampling Merge), ADR-0018 (Prompt Layering), ADR-00xx (Reasoning Levels)
Supersedes: Will partially supersede marker portion of ADR-0014 upon Acceptance (see Deprecation Schedule).

## Context

The current reasoning vs final separation relies primarily on a textual final marker (`===FINAL===`). Harmony Stage 1 added buffered tag parsing (`<analysis>...</analysis><final>...</final>`), but still does not exploit the native channel structure the gpt-oss family was trained on (Harmony response format).

OpenAI Harmony defines:

* Structural tokens: `<|start|>`, `<|channel|>`, `<|message|>`, `<|end|>`, `<|return|>`, `<|call|>`, `<|constrain|>`.
* Channels: `analysis` (chain-of-thought), `commentary` (user-visible planning/tool preludes), `final` (user answer).
* Termination: `<|return|>` (normal completion) or `<|call|>` (tool call request), with subsequent history canonicalization (`<|return|>` → `<|end|>`).

Relying on a marker string is fragile: models may omit it, causing reasoning tokens=0 and masking quality diagnostics. Channels provide first-class, trained structure; adopting them reduces prompt overhead and increases compliance.

## Decision

Implement an incremental Harmony Channel Parser (HCP) state machine to replace marker-based splitting when `llm.prompt.harmony.enabled=true && llm.harmony.channels_parser.enabled=true`.

### Objectives

1. Stream reasoning (analysis) and final answer concurrently on dedicated SSE events (`analysis`, `token`).
2. Drop chain-of-thought from history automatically when previous sampling ended in `final` channel.
3. Maintain backward-compatible fallback: if no channel tokens detected within an initial safety window (N characters / T ms), downgrade to marker mode.
4. Provide observability: metrics for channel compliance, absence, mismatches, and ratio.

### State Machine Outline

States: `AwaitStart`, `Header`, `Channel`, `MessageContent`, `ToolCall`, `Terminated`.

Buffers:

* `header_buf` (collect until `<|message|>`)
* `channel_name` (parsed after `<|channel|>`)
* `content_buf` (flushed on `<|end|>`, `<|return|>`, `<|call|>`)

Transitions:

* Detect `<|start|>` → `Header`.
* Within header, collect until `<|channel|>` (optional) then parse channel token sequence until `<|message|>`.
* After `<|message|>` accumulate content bytes; on `<|end|>` emit message event for that channel.
* On `<|return|>` emit final message (channel must be `final`), set `terminated` flag, stop provider iteration.
* On `<|call|>` capture tool call request (channel `commentary` or `analysis`), emit tool_call event, then stop for external execution.

### Emission Rules

* `analysis` channel: stream deltas as SSE `analysis` (unless `drop_from_history=false`, still not persisted).
* `commentary`: stream as `commentary` (future UI optional); persisted if flagged safe.
* `final`: stream as existing `token` events.
* Usage metrics aggregate per-channel token counts.

### Metrics

* `harmony_channel_messages_total{channel}`
* `harmony_channel_unexpected_order_total` (e.g., final before any analysis when reasoning level > low)
* `harmony_channel_parse_errors_total` (invalid token nesting)
* `harmony_marker_fallback_total` (parser aborted → marker mode used)
* `reasoning_ratio_alert_total` (reuse existing threshold logic across both modes)

### Config Additions

```yaml
llm:
  harmony:
    channels_parser:
      enabled: false
      fallback_on_timeout_ms: 600
      min_tokens_before_fallback: 32
      require_final_channel: true
      drop_commentary_from_history: true
```


### Deprecation Plan (Marker)
Phase 0 (now): Marker mode + optional buffered tags.
Phase 1: Incremental parser behind flag (default off). Collect metrics only.
Phase 2: Enable parser by default for gpt-oss models (keep marker injection as redundant safety; log if unused).
Phase 3: Remove marker injection for gpt-oss; keep legacy path for non-Harmony models (e.g., phi) until they migrate or have their own parser adapters.
Phase 4: Remove marker code after all models have channel-native split implementations.

### Model Adapter Abstraction

Introduce interface `StreamingStructureAdapter`:

```python
class StreamingStructureAdapter(Protocol):
  def process_chunk(self, text: str) -> Iterable[StructuredEvent]: ...
  def finalize(self) -> Iterable[StructuredEvent]: ...
```
Adapters:

* `MarkerAdapter` (existing logic)
* `HarmonyChannelAdapter`
* Future: `PhiMiniAdapter` (if phi uses different or no structural tokens)

Selection: based on model passport capability flags + config.

### Testing Strategy

* Unit: tokenization fragments reconstruct channel messages (including boundary splits mid-token string).
* Unit: fallback when `<|start|>` never appears.
* Integration: analysis+final sample (from captured real output) yields correct sequencing + metrics.
* Integration: tool call sample stops at `<|call|>` with partial conversation context exported.
* Property test: random insertion of noise tokens does not corrupt earlier parsed messages.

### Performance

Overhead target < 3% vs raw pass-through; parser uses single pass with small ring buffer for potential partial special token detection.

### Security & Privacy

Maintain exclusion of `analysis` channel from persisted history; optionally allow `commentary` if flagged safe (config default drop). Tool call JSON bodies sanitized before logging (no user PII). No structural token leakage to user UI except sanitized final answer.

## Alternatives Considered

* Continue marker + tag hybrid: leaves model under-utilizing its trained structural priors.
* Full re-tokenization with tiktoken: more accurate token counts but unnecessary for structural split; skip for latency.
* JSON framing protocol: larger token overhead, more brittle if model deviates.

## Risks

* Partial special token sequences split across provider chunks → must buffer small tail (max len of longest special token pattern).
* Some third-party quantizations might alter tokenization; need disable feature via passport flag.
* Edge case: extremely long analysis spam before final—still truncated by existing reasoning cap logic; channel parser must honor cap.

## Adoption Checklist

* [ ] Implement `StreamingStructureAdapter` interface.
* [ ] Port current marker splitter to `MarkerAdapter`.
* [ ] Implement `HarmonyChannelAdapter` incremental parser.
* [ ] Wire selection logic in generate route.
* [ ] Add metrics + Prometheus registration.
* [ ] Add config keys & documentation (Config-Registry.md).
* [ ] Add tests (unit + integration + perf micro-benchmark).
* [ ] Update [[ADR-0014-Postprocessing-Reasoning-Split]] status: reference supersession for gpt-oss path.
* [ ] Update API.md (new SSE events analysis/commentary, deprecation note for marker).
* [ ] Snapshot state (STATE_SNAPSHOT_YYYY-MM-DD.md).


 
## Decision Outcome
Accepted. Prototype merged behind feature flag; baseline perf within target (<3% overhead). Marker path now designated legacy for Harmony-capable models (see updated ADR-0014 supersession section). Remaining checklist items (tool call handling, commentary channel persistence policy, extended metrics) tracked in backlog.
