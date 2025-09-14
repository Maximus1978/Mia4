# 2025-09-09 — B6 ReasoningPresetApplied v2 + Test Isolation + KPI Cancel

- ADR-0030: ReasoningPresetApplied v2 (preset, mode baseline/overridden, overridden_fields).
- Event emission adjusted (generate after-merge; agent_ops baseline).
- Generated-Events and Events tables updated.
- Added autouse pytest fixture for config/env isolation.
- Added integration KPI test for cancel latency (<500ms).
- Sampling: tag mode=custom in merged_sampling when user overrides are present.
