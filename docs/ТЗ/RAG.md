# RAG (Retrieval-Augmented Generation)

Это индекс-страница пакета документации RAG. Цель: описать модуль извлечения контекста (hybrid BM25 + vector + optional expansion) для построения промпта с наблюдаемостью, тестируемостью и управлением через конфиг/ADR.

Состав пакета:

- Архитектура и потоки: `RAG/Architecture.md`
- Интерфейсы и контракты: `RAG/Interfaces.md`
- Данные и схемы: `RAG/Data-Schemas.md`
- События и метрики: `RAG/Events-and-Metrics.md`
- Конфигурация (proposed): `RAG/Config-Proposed.md`
- Тестирование и оценка качества: `RAG/Testing-and-Eval.md`
- Безопасность и приватность: `RAG/Security-and-Privacy.md`
- ADR (решение по каркасу и контрактам): `../ADR/ADR-0032-RAG-Module-and-Contracts.md`
- README (оглавление пакета): `RAG/README.md`
- Глоссарий: `RAG/Glossary.md`
- Датасет для оценки: `RAG/Evaluation-Dataset.md`
- Нормализация и фьюжн скорингов: `RAG/Normalization-and-Scoring.md`

Быстрый обзор:

- Процесс: intent → (opt) expansion → hybrid retrieve (BM25 + vector) → fusion/rerank → context build (budget, dedupe) → событие RAG.ResultsReady.
- Источники: диалоги, инсайты, документы (ingest). Эмоции — метаданные, не влияют на retrieve напрямую.
- Наблюдаемость: события RAG.* и метрики retrieval_latency_ms, hit@k, mrr, context_tokens и др. (см. раздел метрик).

Примечание: эта страница — индекс. Подробности раскрыты в файлах внутри `docs/ТЗ/RAG/`.

