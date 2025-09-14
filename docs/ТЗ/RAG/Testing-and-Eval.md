# RAG Testing and Evaluation

We follow the pyramid: unit → contract → integration → perf smoke → regression.

## Unit tests

- Normalization: empty/null, language detection stub
- Fusion: min-max normalization with epsilon; weight extremes; identical scores
- ContextBuilder: dedupe logic; budget enforcement; citation assembly
- No-op mode: rag.enabled=false returns empty results

## Contract tests

- Events presence: RAG.QueryRequested and RAG.ResultsReady emitted
- payload shapes: items[], timings_ms present
- Config bi-directional: new keys exist, no removed keys required

## Integration tests

- End-to-end retrieval with in-memory indices (BM25 + vectors)
- Degraded path: one index fails → partial results + debug.degraded=true

## Perf smoke

- Snapshot retrieval_latency_ms p50/p95
- Observe context_tokens distribution vs window size

## Evaluation (offline)

- hit@k and mrr on small eval set (curated)
- Track over time; thresholds per Config-Registry perf.* keys if applicable

## Tooling

- scripts to generate eval reports under reports/
- tests to assert presence and bounds

