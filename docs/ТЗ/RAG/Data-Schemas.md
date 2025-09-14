# RAG Data Schemas

Canonical data shapes for RAG, aligned with Events.md and Config registry.

## Chunk

```json
{
  "id": "uuid",
  "source_id": "doc-or-dialog-id",
  "type": "dialog|insight|document",
  "text": "...",
  "tokens": 123,
  "created_ts": 1736539200.123,
  "meta": { "emotion_hint": "neutral?", "tags": ["foo","bar"] }
}
```

## EmbeddingRecord

```json
{
  "id": "uuid",
  "doc_id": "source_id",
  "modality": "text",
  "vector": [0.1],
  "dim": 1024,
  "model_ref": "bge-m3",
  "chunk_index": 0,
  "metadata": {"lang":"ru"}
}
```

## RetrievalRequest

```json
{
  "query_text": "...",
  "strategies": ["HYBRID"],
  "filters": {"lang":"ru"},
  "top_k": 8,
  "rerank": false
}
```

## RetrievalBundle

```json
{
  "matches": [
    {"id":"uuid","score":0.82,"strategy":"HYBRID","components":{"score_sem":0.7,"score_bm25":4.2}}
  ],
  "debug": {"timings_ms": {"lexical":6,"dense":9,"fusion":2}, "used_strategies":["DENSE","LEXICAL"], "expansion_used": false}
}
```

