# Config Registry

Authoritative listing of public configuration keys exposed to UI / tests. Changes require ADR or changelog entry.

| Key Path | Type | Default | Description | Introduced |
|----------|------|---------|-------------|------------|
| llm.generation_initial_idle_grace_s | float | 45.0 | Initial grace period (seconds) before timeout enforcement on first token generation. Allows model load/warmup time. | 2025-09-30 |
| llm.postproc.reasoning.ratio_alert_threshold | float | 0.45 | Threshold (fraction) at/above which reasoning ratio alert badge appears. | 2025-09-18 |
| llm.primary.require_gpu | bool | false | If true, blocks provider load when GPU initialization fails instead of falling back to CPU. Ensures performance-critical models run on GPU only. | 2025-09-30 |

Notes:

- `generation_initial_idle_grace_s`: Backend timeout enforcement; not exposed to UI but tested in integration suites.
- `reasoning_ratio_threshold`: UI fetches this via `/config` as `reasoning_ratio_threshold`. Must remain within [0.05, 0.95] client clamp window to prevent degenerate UX. Changes require updating related contract tests (ratio alert badge logic).
- `require_gpu`: Deployment-level enforcement; prevents slow CPU fallback in production. Test coverage in `tests/core/test_require_gpu.py`.

