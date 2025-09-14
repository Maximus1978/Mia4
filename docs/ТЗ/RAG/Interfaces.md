# RAG Interfaces and Contracts

This document specifies the RAG public contracts to be implemented in code. Any change requires ADR and tests.

## Data Types (proto)

- EmbeddingRecord: { id, doc_id, modality, vector[dim], dim, model_ref, chunk_index, metadata }
- VectorMatch: { id, score, strategy, components: { score_sem?, score_bm25? } }
- RetrievalRequest: { query_text, strategies[], filters{}, top_k, rerank?: bool }
- RetrievalBundle: { matches: VectorMatch[], debug: { timings_ms, used_strategies[], expansion_used?: bool } }

## Protocols (Python typing)

- VectorStore
  - upsert(records: list[EmbeddingRecord]) -> None
  - query(query: Query, top_k: int) -> list[VectorMatch]
- Retriever
  - retrieve(request: RetrievalRequest) -> RetrievalBundle

## Strategies

Enum Strategy: DENSE | LEXICAL | HYBRID | PATTERN | MULTI_MODAL (future)

Rules:

- HYBRID means compute DENSE and LEXICAL then fuse
- PATTERN is for heuristic/regex lookups (future)

## Fusion and Normalization

- Normalization: per-batch min-max with epsilon (configurable alternative: z-score)
- Fusion formula (default): final = w_sem*norm_sem + w_bm25*norm_bm25
- Config keys in Config-Proposed.md

## Context Builder Contract

Input: list[VectorMatch] + source metadata; Output: ContextBundle

- Dedupe by source_id
- Enforce token budget (<= 0.8 of context window by config)
- Attach citations and provenance

## Error Semantics

- On partial failure, return degraded results and include debug.degraded=true
- Do not raise for expansion timeout; record metric and continue

## Compatibility

See ADR-0019 for rationale and ADR-0032 for acceptance criteria.
