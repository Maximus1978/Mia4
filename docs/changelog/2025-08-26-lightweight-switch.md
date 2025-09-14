# 2025-08-26 Lightweight Model Switch

## Changed

- Lightweight LLM id updated: `phi-3.5-mini-instruct-q4_0` → `phi-3.5-mini-instruct-q3_k_s`.
  - Reason: repeated load failure `invalid vector subscript` (suspected truncated / corrupt Q4_0 file); smaller Q3_K_S quant verified via SHA256 (480fce5d...) and successful streaming.

## Performance (3 runs, prompt 'ping', 48 tokens)

Primary (gpt-oss-20b-mxfp4): first_ms cold ~12.29s then ~26ms; decode_tps ≈ 42–46.

Lightweight (phi-3.5-mini-instruct-q3_k_s): first_ms cold ~12.54s (includes initial provider creation) then ~8–9ms; decode_tps ≈ 143.

## Notes

- Cold first token latency for lightweight dominated by llama.cpp initialization; steady-state meets Gate 3.7 (<1s first token after warm start for UI streaming).
- README and Config-Registry updated; fetch script still references old id (backlog to adjust arguments / defaults).
