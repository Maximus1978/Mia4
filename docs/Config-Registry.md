# Config Registry

Authoritative listing of public configuration keys exposed to UI / tests. Changes require ADR or changelog entry.

| Key Path | Type | Default | Description | Introduced |
|----------|------|---------|-------------|------------|
| llm.postproc.reasoning.ratio_alert_threshold | float | 0.45 | Threshold (fraction) at/above which reasoning ratio alert badge appears. | 2025-09-18 |

Notes:

- UI fetches this via `/config` as `reasoning_ratio_threshold`.
- Must remain within [0.05, 0.95] client clamp window to prevent degenerate UX.
- Changes require updating related contract tests (ratio alert badge logic).
