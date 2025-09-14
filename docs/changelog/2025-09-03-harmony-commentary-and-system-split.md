# 2025-09-03 Harmony Spec Alignment (System/Developer & Commentary Channel)

Scope:

- System / Developer message construction now strictly follows Harmony spec:
  - Identity line fixed to: `You are ChatGPT, a large language model trained by OpenAI.`
  - Added lines: `Knowledge cutoff: 2024-10`, runtime `Current date: YYYY-MM-DD`, `Reasoning: <low|medium|high>`.
  - Canonical channel declaration line added (wrapped for width but content preserved).
- Developer message auto-prefixes `# Instructions` if missing.
- Commentary channel parsing & streaming introduced (pass-through, not counted in reasoning/final token stats) with metrics per-channel via `harmony_channel_tokens_total{channel=commentary}`.
- Adapter updated to accept `<|channel|>commentary` and emit `event: commentary` SSE frames.

Metrics:

- Extends `harmony_channel_tokens_total` with `channel=commentary`.

Docs:

- `API.md` updated (commentary description, cancellation section clarified).

No breaking changes for clients already consuming `analysis` / `token` / `final` events; `commentary` is additive.

Next (pending): cancellation endpoint + generation_cancelled_total, max token cap finalization.
