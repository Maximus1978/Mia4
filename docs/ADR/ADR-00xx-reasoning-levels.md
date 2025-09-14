# ADR-00xx: Reasoning Levels Integration (low / medium / high)

Status: Accepted
Date: 2025-08-29
Supersedes: –
Related: Post-processing splitter ADR (marker-based reasoning separation)

## Context

We expose three reasoning "effort" levels (low, medium, high) similar to gpt-oss model guidance. Previously presets only adjusted sampling (temperature, top_p). We now:

1. Bind each preset to a reasoning token budget (`reasoning_max_tokens`).
2. Inject a concise instruction into the effective system prompt to request the model modulate internal chain-of-thought depth and stop at a marker before the final answer.
3. Keep reasoning hidden (default) while still capturing aggregate metrics (reasoning_tokens, final_tokens, ratio) for observability.

## Decision

Add `reasoning_max_tokens` to every entry under `llm.reasoning_presets` in config. During `/generate`:

* Server copies base postproc config and overrides `postproc.reasoning.max_tokens` with preset-specific value.
* Sampling overrides (temperature, top_p, etc.) remain supported.
* (Historical) Marker-based splitter buffered reasoning until final segment (now Harmony channels).
* Optional emission of full reasoning as SSE `reasoning` event only when `drop_from_history=false` (default true to avoid retention / exposure risks).

Prompt layer: when building effective prompt if system prompt does not yet contain the marker instruction, we append an instruction block including the marker token. We extend that block to include preset guidance (see below) using the selected reasoning level placeholder.

## Prompt Addendum (per request)

Example injection (simplified):

```text
[REASONING LEVEL]
Current reasoning effort: <LOW|MEDIUM|HIGH>.
- LOW: Provide only minimal internal steps (succinct outline) before the marker.
- MEDIUM: Provide a concise but complete chain sufficient to justify the answer.
- HIGH: Provide a thorough, multi-step chain exploring edge cases before the marker; avoid redundant loops.
Historical format (superseded): reasoning tokens then marker line then final answer.
```

Low/Medium/High mapping is deterministic; no user override required for now.

## Rationale

* Direct alignment with published gpt-oss guidance: reasoning effort levels as latency / quality trade-off.
* Server-side enforcement of token budget ensures predictable costs regardless of model verbosity.
* Separation of sampling vs reasoning length avoids conflating diversity controls with reasoning depth.
* Hidden-by-default reasoning reduces leakage while still enabling monitoring and metrics.

## Alternatives Considered

1. Direct streaming of reasoning tokens intermixed with answer — rejected (UI flicker, harder separation).
2. Using stop sequences instead of explicit marker — less reliable; marker simpler to detect deterministically.
3. Client-side truncation only — cannot guarantee consistent metrics server-side.

## Consequences

* Config schema extended implicitly (no code schema change needed since dict values are flexible) — documentation updated.
* Tests must cover: preset changes reasoning_max_tokens, low < medium < high, truncation at boundary, metrics reflect cap.
* Future: could add dynamic adaptive increase (auto-escalate medium→high if uncertainty heuristics fire) using same mechanism.

## Follow-up Tasks

* Add integration tests verifying per-preset max reasoning tokens.
* UI: surface reasoning max (e.g., badge "R cap: 256").
* Telemetry: histogram of reasoning_tokens / cap saturation ratio.
* Consider live `reasoning_delta` stream behind feature flag.

## Security / Privacy

Reasoning remains excluded from history unless explicitly enabled; prevents inadvertent long-term storage of potentially sensitive model introspection content.

## Status Log

2025-08-29: Initial adoption and backend implementation complete.
