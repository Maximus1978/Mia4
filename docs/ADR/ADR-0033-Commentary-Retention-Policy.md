# ADR-0033 — Commentary Retention Policy

Status: Proposed

Context

We support multiple commentary retention modes (metrics_only, hashed_slice, redacted_snippets, raw_ephemeral). We need a formal policy governing when each mode applies, tool-chain overrides, and privacy guarantees.

Decision

- Define allowed modes and semantics:
  - metrics_only: no payload retention; only counters.
  - hashed_slice: deterministic SHA-256(hex16) over first N chars; no raw text.
  - redacted_snippets: short snippets with regex redaction applied; placeholder replacement.
  - raw_ephemeral: transient in-memory store with TTL; not persisted.
- Tool chain override: if tool commentary is detected, enforce override_mode (default hashed_slice) when apply_when matches.
- Store-to-history is disallowed by default; explicit opt-in via config.

Consequences

- Observability: emit metrics on every override/downgrade/fallback event.
- Security: no PII logs for commentary flows; redact or hash prior to any structured logging.

Config Keys (reference)

- llm.commentary_retention.* (see Config-Registry.md)

Testing

- Unit: mode selection logic; regex redaction edge cases.
- Contract: retention mode events/flags present.
- Integration: ephemeral TTL expiry; no persistence.
