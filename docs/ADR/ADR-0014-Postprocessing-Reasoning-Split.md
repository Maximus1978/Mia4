# ADR-0014: Postprocessing Reasoning Split (ARCHIVED)

Status: Accepted (Partially Superseded for Harmony-capable models)
Date: 2025-08-28 (updates: 2025-08-29 Harmony Stage 1, 2025-09-01 leakage remediation, 2025-09-01 supersession note)
Authors: MIA Core
Supersedes: None
Related: ADR-0007-Streaming-and-Context-Budget, ADR-0008-system-prompt-layering, ADR-0012-GenerationResult-Contract

## Context

Large language model outputs often blend internal chain-of-thought (reasoning) with the final user-facing answer. For product safety, UX clarity, and memory governance we must:

- Avoid persisting raw reasoning into long-term chat history (retention & leakage risk).
- Provide transparent access to the most recent reasoning for debugging / trust (ephemeral, collapsible in UI, not stored).
- Enable metrics on reasoning vs final token proportions to detect drift (excessive reasoning wastes latency & tokens).

Originally we adopted a lightweight, model-agnostic streaming post-processing layer that splits reasoning from answer using an explicit final marker inserted via system prompt directive. This avoided fragile heuristic parsing and kept backward compatibility.

As of ADR-0020 (Harmony Streaming Migration) the marker mechanism is CLASSIFIED AS LEGACY for models that emit Harmony channel tokens (`analysis`, `final`, optional `commentary`). This ADR remains authoritative ONLY for providers without native Harmony channels or when the Harmony channel parser is disabled/fallback triggers.

## Decision (Legacy Path)

Introduce a configurable post-processing pipeline (`llm.postproc`) that wraps provider token streams and emits transformed events:

- Input: iterator of raw text chunks (opaque to structure).
- Output: sequence of dict events with types: `delta` (final answer tokens only) and a single `final` summarizing stats.

Key behaviors:

1. (ARCHIVED) Legacy marker split removed; replaced by Harmony channel parser.
2. No-Marker Fallback: If no marker encountered by stream end, entire output treated as answer (reasoning_tokens=0).
3. Truncation: Reasoning token count capped at `reasoning.max_tokens`; beyond limit triggers forced transition to answer mode and appends remaining buffered text as answer tokens.
4. Drop From History: When `drop_from_history=True`, reasoning text is excluded from `final` event (`reasoning_text=None`) so upstream does not persist it.
5. N-gram Suppression: Sliding window dedup (`ngram.n`, `ngram.window`) suppresses immediate repetitive n-grams in both reasoning and answer to mitigate provider duplication bursts (e.g. llama.cpp delta echo issues).
6. Whitespace Collapse: Optional normalization to reduce irregular spacing noise (`collapse.whitespace=True`).
7. Metrics: Final event includes `stats`: `reasoning_tokens`, `final_tokens`, `reasoning_ratio` (float 0..1; 0 if denominator=0). Exposed further in `GenerationCompleted.result_summary.reasoning` and `usage` SSE frame.
8. Idempotent System Prompt Injection: Backend augments configured system prompt at request time (not hashed) with clear directive instructing model to output the final marker on a separate line just before the final answer.

## Alternatives Considered

- Heuristic Split (e.g., regex on phrases like 'Final Answer:') — rejected due to instability across languages and prompt variants.
- Multi-message role formatting (reasoning as separate assistant role) — would still risk persistence & ambiguous boundaries.
- Model fine-tuning to internalize separation — higher cost, less transparent, slower iteration.
- JSON streaming schema — adds verbosity; token-level latency penalties; reduces human legibility.

## Consequences

Positive:

- Deterministic separation with explicit marker; low implementation complexity.
- Unified stats enabling governance and perf optimization (detect reasoning bloat).
- Reasoning never persisted to session store when configured (privacy & cleanliness).

Neutral/Trade-offs:

- Requires cooperative model behavior; if marker missing we lose split (handled gracefully).
- Marker string slightly increases prompt size (negligible); could leak if user copies full reasoning sidebar.
- Postproc adds minimal overhead (string ops + n-gram set membership).

Risks & Mitigations:

- Marker collision in user prompt: improbable; marker chosen as high-entropy style token; can be made rarer if needed (configurable).
- Model ignores instruction: fallback ensures no crash; telemetry can surface `reasoning_ratio==0` patterns.
- Excess reasoning tokens causing latency: truncate early at `max_tokens`.

## Backward Compatibility

- Existing providers unchanged; wrapper sits in route layer only.
- `GenerationCompleted.result_summary` extended with optional `reasoning` object (additive, non-breaking per ADR-0012 rules).
- Absence of `llm.postproc` config defaults to enabled with sensible defaults.

## Config Keys

```text
llm.postproc.enabled (bool, default True)
(Removed) legacy marker key deleted – Harmony channels mandatory.
llm.postproc.reasoning.max_tokens (int, default 256)
llm.postproc.reasoning.drop_from_history (bool, default True)
llm.postproc.ngram.n (int, default 3)
llm.postproc.ngram.window (int, default 128)
llm.postproc.collapse.whitespace (bool, default True)
```

## Event & Metric Impacts

- No new core events; enrich `GenerationCompleted.result_summary`.
- Metrics added: `reasoning_tokens`, `final_tokens`, `reasoning_ratio` (emitted inside usage summary; aggregated externally).

## Test Coverage

- Split with marker
- No-marker fallback
- Truncation at max_tokens
- N-gram suppression
- Reasoning not saved (final.reasoning_text is None)

Pending / Future Tests:

- Marker collision edge case (synthetic prompt containing marker).
- Performance microbenchmark (overhead <1% wall time typical generation).

## Harmony Channels Supersession Summary (See ADR-0020)

ADR-0020 introduces an incremental Harmony Channel Parser (HCP) that consumes structural tokens `<|start|>assistant<|channel|>{channel}<|message|> ... <|end|>` or `<|return|>`. When the channels parser is active and channels are detected, the logic in this ADR (marker split) is bypassed entirely. Fallback to this legacy path occurs only when:

1. Harmony feature flag disabled.
2. Structural channel tokens not detected within the configured safety window.
3. Model passport lacks Harmony capability.

All governance concepts (reasoning_tokens, reasoning_ratio, drop_from_history, n-gram suppression, whitespace collapse) remain semantically consistent between both paths. Metric continuity is preserved: counts reported by the Harmony adapter map 1:1 to legacy stats fields.

## Future Extensions

- Multiple marker variants or automatic detection for multilingual fallback.
- Structured JSON side-channel for reasoning (channel-level versioning).
- Adaptive reasoning truncation based on latency budget.
- Inline repetition penalty interplay with n-gram suppression (opt-in).

## Decision Outcome

Adopted. Marker mode (baseline) + Harmony Stage 1 implemented. Incremental streaming & mismatch metrics deferred (tracked in instructions backlog). Snapshot created (2025-08-29) for transition to Phase 3 planning.

## 2025-09-01 Remediation (Reasoning Leakage Hotfix)

Issue (2025-08-31): Observed leakage of internal chain-of-thought (English reasoning text + service tokens like `<|start|>assistant`) into final user answer despite `drop_from_history=true`.

Root causes:

1. Missing service token filtering (raw `<|...|>` tokens passed through).
2. Over-aggressive whitespace collapse leading to word concatenation.
3. Absence of heuristic leak detection (silent failures when marker absent).

Remediation Implemented (Sprint 3A Hotfix):

1. Service Token Filter: Regex removal of `<|...|>` tokens and trailing channel markers (`|final`, `|analysis`, `|assistant`).
2. Whitespace Normalization: Replace runs of whitespace with a single space using pattern `(\\s)\\1+`; preserve single spaces (no word gluing).
3. Leak Metric: `reasoning_leak_total{mode=marker}` increments when dropped reasoning prefix (first 24 chars) appears in final output.
4. Integration Test: No-marker fallback path asserts absence of `reasoning_leak_total` counter and no reasoning text surfaced.
5. Unit Test: Whitespace collapse behavior (multi-spaces & newlines → single space; words not concatenated).

Non-goals (Deferred): Harmony tag streaming (Stage 2), advanced semantic leak detection, multi-language marker variants.

Backward Compatibility: Additive changes—`leak_detected` optional field in final postproc event; metric is optional for downstream dashboards (absent implies zero leaks).

Status: ISSUE marked Resolved in instructions (section 4.9). Future improvements tracked under Harmony Stage 2 backlog.

## Ephemeral Reasoning UX Pattern (2025-09-05 Addition)

Objective: Provide transparent access to the most recent chain-of-thought for debugging without persisting it beyond the active response.

Contract:

- Streaming channel `analysis` supplies incremental reasoning tokens.
- If `llm.postproc.reasoning.drop_from_history=true` then the final adapter event MUST set `reasoning_text=null` (never materialize full reasoning in stored history structures).
- UI may buffer streamed tokens in volatile memory and display a collapsible panel (e.g. button "Reasoning" → expand). Panel content is discarded on any new generation request.
- When `drop_from_history=false`, adapter includes `reasoning_text` in final event (auditable / offline review mode).

Non-Goals:

- Server-side caching beyond in-flight request lifetime.
- Persisting reasoning across sessions or adding export endpoints.

Test Coverage Added (2025-09-05):

- `test_ephemeral_reasoning_drop_from_history_true` ensures suppression.
- `test_reasoning_retained_when_drop_from_history_false` ensures inclusion.

Security / Privacy Rationale:

- Minimizes exposure surface by default; developers must explicitly opt-in to retention by flipping a single boolean.
- Prevents accidental logging of potentially sensitive intermediate reasoning.


## Migration Note (2025-09-01 Supersession Update)

ADR-0020 Accepted: marker directive injection MUST NOT be used for Harmony-capable models when `llm.harmony.channels_parser.enabled=true`. This ADR persists for:

- Non-Harmony providers (no structural channel capability flag).
- Explicit fallback cases (parser timeout / no channel start seen).

Deprecation phases, parser metrics, and adoption KPIs now governed exclusively by ADR-0020.

Cross-links:

- ADR-0020-Harmony-Streaming-Migration-Plan.md
- API.md (SSE events: forthcoming `analysis` channel)
- STATE_SNAPSHOT_2025-08-29.md (baseline prior to incremental parser)

