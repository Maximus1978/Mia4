# RAG

Кратко: модуль извлечения контекста (hybrid BM25 + vector + optional expansion) для построения промпта.

## Процесс

1. Detect intent / нормализация.
2. (Optional) Query expansion.
3. Hybrid retrieve (BM25 + vector).
4. Re-rank (score fusion).
5. Build context (token budget, dedupe).
6. Emit RAG.ResultsReady.

## Что индексируем

- Диалоги (role=user|assistant, ts, emotion_tag).
- Инсайты (summary, novelty_score).
- Документы (source=file / ingest).

## Формат chunk

{ id, source_id, type, text, tokens, created_ts, meta{emotion_hint?, tags[]} }

## События

- RAG.QueryRequested {query, user_id, time}
- RAG.ResultsReady {query, top_k, items[]}
- RAG.IndexRebuilt {count, duration_ms}

Canonical definitions: `Events.md` (эта секция обзорная).

## Метрики

| Metric | Описание | Цель |
|--------|----------|------|
| retrieval_latency_ms | время 2–5 шага | <120 |
| hit@5 | релевант среди top5 (eval set) | >0.7 |
| mrr | средняя обратная позиция | рост |
| context_tokens | итоговые токены в prompt | <=0.8 окна |

## Алгоритмы (используемые)

| Этап | Техника |
|------|---------|
| Lexical | BM25 (rank-bm25) |
| Vector | bge-m3 embeddings |
| Fusion | `score = w_sem * norm_sem + w_bm25 * norm_bm25` |
| Expansion (opt) | lightweight LLM rewrite |

## Стратегии

| Стратегия | Назначение | Статус |
|-----------|-----------|--------|
| Hybrid (semantic+bm25) | Основной retrieve | Active |
| Query Expansion | Уменьшить пропуски | Optional |
| Relevance Feedback | Адаптация весов | Planned |
| Multi-hop | Сложные вопросы | Planned |

## Границы

Эмоции не регулируют retrieve (только метаданные). Vision/ingest → поставщики документов.

## Memory Integration

Использует MemoryQuery контракт (см. `Memory.md`). Поля необходимых сущностей: DiaryEntry.text, DiaryEntry.ts, Insight.summary.

## Нормализация скорингов (skeleton)

| Component | Raw Score Symbol | Normalization Method | Formula Placeholder | Notes |
|-----------|------------------|----------------------|--------------------|-------|
| Semantic | score_sem | min-max / z-score (decide) | norm_sem = ... | |
| BM25 | score_bm25 | min-max / log scaling (decide) | norm_bm25 = ... | |
| Fusion | final_score | weighted sum | final = w_sem*norm_sem + w_bm25*norm_bm25 | weights config |

TODO: choose method (likely per-batch min-max with epsilon).

