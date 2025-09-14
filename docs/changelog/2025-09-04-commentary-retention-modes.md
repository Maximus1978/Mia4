# 2025-09-04: Commentary Retention Modes Implemented

Status: Shipped

Implements ADR-0025 (now Accepted) introducing multi-mode commentary retention:

Modes:

- metrics_only (default) – only token metrics, no text stored
- hashed_slice – store hash prefix + bounded slice length only
- redacted_snippets – pattern-redacted bounded snippet + redaction count metric
- raw_ephemeral – raw text cached in-memory with TTL, not persisted

Metrics:

- commentary_retention_mode_total{mode}
- commentary_retention_redactions_total
- commentary_tokens_total{model}

Tests Added:

- test_harmony_retention_modes.py covering hashed_slice, redacted_snippets, raw_ephemeral
- Existing summary test extended implicitly via adapter logic

Privacy / Safety:

- No persistent storage beyond selected minimal summary fields
- raw_ephemeral never leaves process; periodic prune

Follow-ups:

- Leak safeguard toggle for tool chain commentary (Execution Plan #9)
- Document retrieval endpoint for ephemeral (if product need emerges)
- Config-Registry.md entry for new nested keys (pending)
