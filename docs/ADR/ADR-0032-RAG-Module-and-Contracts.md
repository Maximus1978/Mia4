# ADR-0032: RAG Module and Contracts

Status: Proposed
Date: 2025-09-12

## Context

We need to implement a minimal-yet-solid RAG skeleton with hybrid retrieval, observable events, and config-driven behavior, without locking into a specific backend. ADR-0019 defined a skeleton; this ADR formalizes contracts, config keys, and acceptance criteria for the first increment.

## Decision

Adopt the following:

- Public interfaces in code for VectorStore and Retriever as per `docs/ΤЗ/RAG/Interfaces.md`
- Data schemas in `docs/ΤЗ/RAG/Data-Schemas.md`
- Events and metrics in `docs/ΤΖ/RAG/Events-and-Metrics.md`
- Proposed config keys in `docs/ΤΖ/RAG/Config-Proposed.md` merged into Config Registry

## Alternatives

- Single-store tight coupling (rejected)
- Implement rerank from day one (deferred)

## Consequences

- Enables UI placeholders and observability
- Facilitates future switch of dense/lexical backends

## Acceptance Criteria

- Unit + contract tests pass for no-op and hybrid modes
- Events emitted: RAG.QueryRequested and RAG.ResultsReady with timings
- Config bi-directional test green (no missing/removed required keys)
- Perf smoke snapshot created under reports/

## Rollout

- Implement no-op retriever behind rag.enabled=false first
- Add in-memory BM25 + cosine store for tests
- Evaluate on a small curated set; add thresholds later

