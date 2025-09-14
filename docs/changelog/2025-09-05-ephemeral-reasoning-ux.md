# 2025-09-05: Ephemeral Reasoning UX Clarification

Status: Added

Summary:

- Documented explicit ephemeral reasoning pattern: when `llm.postproc.reasoning.drop_from_history=true` the backend suppresses `reasoning_text` (null in final event) and the UI is expected to render a collapsible live panel assembled only from streamed `analysis` tokens, discarded on next request.
- Added core test `test_ephemeral_reasoning.py` validating presence/absence of `reasoning_text` depending on `drop_from_history`.
- Updated `API.md` and ADR-0014 with a dedicated UX section.

Motivation:

- Make transient nature of reasoning explicit for personal / debug usage while keeping persistence off by default (privacy & noise reduction).
- Reduce risk of accidental retention regression (documentation now asserts contract).

Artifacts:

- `tests/core/test_ephemeral_reasoning.py`
- `docs/API.md` (reasoning section amended)
- `docs/ADR/ADR-0014-Postprocessing-Reasoning-Split.md` (Ephemeral Reasoning UX Pattern)

No runtime behavior changes (purely documentation + tests). Metrics unaffected.
