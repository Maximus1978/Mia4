# RAG Security and Privacy

Principles:

- No PII in logs; redact in debug fields
- Respect sandbox roots for ingest; no arbitrary file reads
- Config controls for retention/TTL (future)

Threats:

- Prompt injection via retrieved context → mitigate with citation boundaries and sanitization
- Data poisoning in indices → require provenance and hash checks
- Over-collection of context → enforce token budgets strictly

Operational Controls:

- Structured logs with hashed previews for texts
- Metrics to detect anomalies (sudden spike in retrieval_latency_ms)
- On-call runbooks (TBD)

