# RAG Evaluation Dataset

Purpose: define a minimal, reproducible dataset format and curation rules for offline RAG evaluation (hit@k, MRR).

## Goals

- Small, versioned dataset committed to repo (or generated deterministically)
- Simple JSONL schema for queries and gold passages
- Reproducible scoring scripts and CI-friendly checks

## Schema

- queries.jsonl: one JSON per line
  - id: string (uuid)
  - text: string
  - tags?: string[] (domain, lang)
- corpus.jsonl: one JSON per line
  - id: string (chunk id)
  - source_id: string (doc id)
  - text: string
  - meta?: object (tags, lang, provenance)
- qrels.jsonl: one JSON per line
  - query_id: string
  - doc_id: string (chunk id)
  - relevance: int (0/1)

## Curation

- Prefer short, unambiguous questions; avoid answer leakage from prompt
- Ensure at least one positive per query; include 3–5 hard negatives
- Label in pairs using lightweight process; document disagreements

## Metrics

- hit@k: fraction of queries with at least one relevant doc in top-k
- MRR: mean reciprocal rank of the first relevant doc

## Workflow

1) Build in-memory indices from corpus.jsonl (BM25 + embeddings)
2) Run retrieval for all queries; write results.jsonl (top_k matches per query)
3) Score with qrels.jsonl → hit@k, MRR
4) Store snapshot under `reports/` and compare to previous

## Ownership

- Dataset steward: assign a reviewer
- Changes require PR with diff summary and score impact
