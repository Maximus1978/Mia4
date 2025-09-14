# 2025-09-05: Harmony Duplicate Final Channel Drop

Status: Added

Summary:

- Fixed duplication when two `<|channel|>final` messages appeared back-to-back in a single provider chunk.
- Adapter now ignores trailing duplicate final content after first final closure and increments `harmony_unexpected_order_total{type=extra_final}`.
- Prevents user-visible repeated answer text and keeps token accounting stable.

Artifacts:

- Code: `core/llm/adapters.py` (finalize() trailing duplicate branch)
- Test: `tests/core/test_harmony_duplicate_final.py`

No config changes. Metrics: existing unexpected order counter reused.
