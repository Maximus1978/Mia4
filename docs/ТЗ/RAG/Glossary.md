# RAG Glossary

- RAG — Retrieval-Augmented Generation: pipeline that retrieves context chunks to ground the LLM answer.
- Chunk — minimal retrievable unit (paragraph/slice) with metadata; see Data-Schemas.md.
- Strategy — retrieval mode: DENSE, LEXICAL, HYBRID, PATTERN (future), MULTI_MODAL (future).
- Fusion — combining scores from multiple strategies after normalization.
- Expansion — optional query rewriting/generation to reduce misses.
- Context budget — token limit allotted for retrieved text before the model prompt.
- Provenance — source information allowing audit of where a chunk came from.
- Re-rank — second-stage model to refine ordering (deferred).
- Collection — named index namespace (e.g., "memory", "docs").
