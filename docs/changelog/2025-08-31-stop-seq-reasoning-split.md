# 2025-08-31 Stop Sequences & Reasoning Split Completion

## Added

- Stop sequence support in `/generate` (user overrides replace config; trimming applied to final_text; emits stop_reason=stop_sequence).
- SSE `usage` event including reasoning stats (reasoning_tokens, final_tokens, reasoning_ratio) and decode_tps.
- System prompt automatic injection of reasoning final marker instructions.
- Reasoning split post-processor integrated (marker mode) with n-gram suppression.
- Sampling origin layering (passport -> preset -> user) surfaced via GenerationStarted.sampling_origin.
- API tests for stop sequence truncation and sampling origin (smoke path).

## Changed

- `GenerationStarted` now includes `stop_sequences` field when active.
- `GenerationCompleted` result_summary extended with reasoning aggregation (under reasoning key) plus stop_reason propagation.
- Added SSE `usage` emission before `final`/`end` for parity with API.md contract.

## Fixed

- Missing `usage` frame in streaming route causing downstream UI assumptions to fail.
- Reasoning text leakage risk: ensured reasoning_text not stored in session history when drop_from_history=True.

## Metrics

- `generation_decode_tps` observed in route for decode throughput.
- `reasoning_buffer_latency_ms` recorded between marker detection and final emission.

## Tests

- Added `tests/api/test_generate_stop_and_reasoning.py` covering stop sequence and sampling layering smoke.
- Extended postproc unit tests already cover ngram suppression and reasoning truncation.

## Follow-ups

- Integrate reasoning_ratio_alert_total end-to-end test.
- Harmony Stage 2 (streaming analysis channel) pending.
- Cancellation endpoint implementation still outstanding.

## Verification

- All new tests green.
- Existing stream tests unaffected.
