# RAG Config (Proposed Keys)

All new keys must be added to `docs/ТЗ/Config-Registry.md` via ADR.

| Key path | Type | Default | Reloadable | Notes |
|----------|------|---------|------------|-------|
| rag.enabled | bool | true | yes | Master switch; when false → no-op retriever |
| rag.top_k | int | 8 | yes | Number of items to retrieve |
| rag.hybrid.weight_semantic | float | 0.6 | yes | Weight of dense score |
| rag.hybrid.weight_bm25 | float | 0.4 | yes | Weight of BM25 score |
| rag.normalize.method | string | minmax | yes | minmax\|zscore |
| rag.normalize.epsilon | float | 1e-6 | yes | Safety for min-max |
| rag.context.max_fraction_of_window | float | 0.80 | yes | Context budget cap |
| rag.expansion.enabled | bool | false | yes | Enable QueryExpander |
| rag.expansion.model | string | lightweight | yes | Model id for expansion |
| rag.collection_default | string | memory | no | Default collection (exists) |

Acceptance criteria and tests: see ADR-0032.

