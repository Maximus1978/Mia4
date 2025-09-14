# Normalization and Score Fusion

We normalize per-retrieval-batch to make semantic and lexical scores comparable.

## Methods

- Min-max (default): norm = (x - min) / max(min_delta, max - min)
- Z-score (optional): z = (x - mean) / stdev; norm = sigmoid(z)

## Fusion

final = w_sem * norm_sem + w_bm25 * norm_bm25
- Weights configured via rag.hybrid.weight_semantic and rag.hybrid.weight_bm25
- Ensure w_sem + w_bm25 = 1.0 in validation

## Edge cases

- Empty results from one strategy → use the other only
- Identical scores → stable sort by doc_id
- NaN/inf → treat as 0 after clipping
