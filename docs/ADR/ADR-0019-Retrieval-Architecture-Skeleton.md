# ADR-0019: Retrieval Architecture Skeleton (Pre-RAG Gate)

Status: Draft
Date: 2025-08-31

## Context

RAG implementation is deferred until performance parity, but we must lock high-level interfaces now to avoid refactors: support hybrid (lexical + dense + pattern) and future multimodal (image/video/sensor) without committing to a single backend.

## Decision

Define neutral interfaces:

```python
class VectorStore:
    def upsert(self, records: list[EmbeddingRecord]) -> None: ...
    def query(self, query: 'Query', top_k: int) -> list['VectorMatch']: ...

class Retriever:
    def retrieve(self, request: 'RetrievalRequest') -> 'RetrievalBundle': ...
```

Data structures (initial):

```python
EmbeddingRecord(id, doc_id, modality, vector, dim, model_ref, chunk_index, metadata)
VectorMatch(id, score, strategy, components: dict)
RetrievalRequest(query_text, strategies, filters, top_k, rerank: bool)
RetrievalBundle(matches: list[VectorMatch], debug: dict)
```

Strategies enum: `DENSE`, `LEXICAL`, `HYBRID`, `PATTERN`, `MULTI_MODAL`.

Fusion: weighted reciprocal rank fusion (configurable weights) with optional rerank stage (cross-encoder) later.

No ingestion pipeline yet: placeholder no-op implementations that always return empty list when `rag.enabled=false`.

## Consequences

- Enables early integration points (UI placeholders, events) without performance cost.
- Facilitates adapter pattern for pgvector → Qdrant migration.

## Alternatives Considered

- Hardwire single store (Chroma) – rejected due to scaling & hybrid limits.
- Implement full ingestion now – rejected (perf gate unmet).

## Testing

- Unit: no-op store returns empty results.
- Contract: retrieval call with multiple strategies returns stable structure.

## Open Issues

- Multi-vector (per modality) scoring normalization specifics.
- Rerank model passport concept.

## Status Transition

Draft → Accepted post interface implementation & tests.
