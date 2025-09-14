# ADR-0025: Commentary Retention Policy

## Status
Accepted (2025-09-04)

## Context
`commentary` channel may contain explanations or contextual side notes. We must control retention (privacy, log size) and still gather metrics.

## Decision
Introduce config key `commentary_retention.mode` with enum (implemented):

- `metrics_only` (default): do not store commentary text; only count tokens
- `hashed_slice`: retain only hash prefix + truncated slice (no raw text)
- `redacted_snippets`: retain bounded snippet with regex redactions + redaction count metric
- `raw_ephemeral`: raw commentary kept only in in-memory TTL cache (not persisted)

Deferred (not implemented):

- `store_persist`: would persist full commentary with PII safeguards (future ADR)

Security posture: no active mode writes full commentary to durable storage; ephemeral cache pruned on access; hashed slice prevents reconstruction; redactions remove sensitive markers.

### Tool Chain Override Extension (2025-09-05)

Added optional conditional override block `commentary_retention.tool_chain`:

```yaml
tool_chain:
	detect: true
	override_mode: hashed_slice
	apply_when: raw_ephemeral  # or "any"
	tag_in_summary: true
```

Behavior:

- Detection heuristic v1: commentary segment starts with prefix `[tool:`.
- If `detect` is true and heuristic matches, summary tagged with `tool_commentary_present=True`.
- If (`apply_when == any` OR matches current base `mode`) AND `override_mode` is set + valid, summary `mode` switched to override.
- Override tagging (when `tag_in_summary=True`): adds `base_mode`, `applied_override=True`.
- Metric `commentary_retention_override_total{from,to}` increments on each applied override.
- Works alongside existing mode metric (`commentary_retention_mode_total`).

Motivation: ensure stricter retention when tool commentary may contain structured arguments or sensitive snippets even if base mode is a looser setting (e.g. `raw_ephemeral`).


## Rationale
Start safest (no storage) while allowing future expansion without breaking contract.


## Metrics

- `commentary_tokens_total{model}` (token counts)
- `commentary_retention_mode_total{mode}` (mode usage)
- `commentary_retention_redactions_total` (redaction occurrences)
- `tool_commentary_sanitized_total` (sanitized tool commentary occurrences)
- `commentary_retention_override_total{from,to}` (override activations)


## Alternatives
Immediate persistence – rejected for privacy.


## Migration
Unknown keys rejected by config tests; add to Config-Registry when modes implemented.


## Next Steps

1. Leak safeguard for tool chain commentary (Execution Plan #9) (baseline sanitation done; deeper heuristics pending)
2. (Done) Add Config-Registry entries for nested mode keys
3. Optional ephemeral retrieval admin endpoint (audit-only)
4. Evaluate need for persistent storage mode + separate ADR
5. Expand detection heuristics (e.g. JSON tool payload markers)


## References
Harmony commentary channel spec
