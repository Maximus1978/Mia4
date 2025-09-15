## 2025-09-14 — Harmony: sliding window, SSE usage, and finalize migration (part 1)

Summary

- Sliding context window: history is included into Harmony prompt with a budget constrained by model context_length, reserving output tokens; earliest turns drop first.
- SSE usage extended: added context_used_tokens, context_total_tokens, context_used_pct; UI shows percentage (prefers SSE values; falls back to /models limits when missing).
- Finalize migration (part 1): echo stripping and final_text now produced in Pipeline; route uses PipelineResult; GenerationCompleted/Cancelled remain emitted by Pipeline.
- API and docs: added GET /presets; documented usage.context_* in docs/API.md; noted approximate calculation; tests/api/test_api_presets.py added.
- Tests: added tests/core/test_sliding_context.py.

Known limitations

- Usage metrics (latency_ms/decode_tps/output_tokens/prompt_tokens) still partially computed in route; next step is to unify in PipelineResult and make the route transport-only.
