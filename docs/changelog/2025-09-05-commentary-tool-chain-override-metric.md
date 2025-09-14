# 2025-09-05 Commentary Tool Chain Override Metric

Added:

- `commentary_retention_override_total{from,to}` metric to track when tool commentary triggers a retention mode override.
- Config registry entries for `llm.commentary_retention.tool_chain.*` keys (detect / override_mode / apply_when / tag_in_summary).
- ADR-0025 updated with Tool Chain Override Extension section and new metrics list.

Behavior:

- On detection of commentary starting with `[tool:` and matching override conditions, adapter switches effective mode and emits tagging fields (`base_mode`, `applied_override`, `tool_commentary_present`).
- Override metric increments per finalization event where mode changes.

Rationale: Strengthen privacy guarantees by enforcing stricter retention when tool chain commentary is present.
