# RAG Events and Metrics

This file extends the canonical `docs/ТЗ/Events.md` with RAG-specific details.

## Events

- RAG.QueryRequested v1
  - Required: request_id, query, user_id, ts
  - Optional: expansion_planned(bool), strategies[], top_k
- RAG.ResultsReady v1
  - Required: request_id, items[], latency_ms
  - Optional: top_k, debug{ used_strategies[], timings_ms, expansion_used }
- RAG.IndexRebuilt v1
  - Required: count, duration_ms
  - Optional: collection

Note: Canonical table lives in `Events.md`. Here we clarify debug payload fields.

## Metrics

- retrieval_latency_ms (histogram) — end-to-end RAG pipeline latency (normalization→fusion→context build)
- expansion_latency_ms (histogram) — time spent in QueryExpander
- expansion_rate (counter) — fraction of requests where expansion_used=true
- hit@k (gauge via eval harness) — relevance in top-k
- mrr (gauge via eval harness) — mean reciprocal rank
- context_tokens (histogram) — tokens included in final context

## Labels (suggested)

- collection, strategy (dense|lexical|hybrid), exp_used (0|1)

## Emission Points

- On QueryRequested: increment rag_query_total
- On ResultsReady: observe retrieval_latency_ms; emit distribution of used strategies
- On IndexRebuilt: increment rag_index_rebuilt_total{collection}

