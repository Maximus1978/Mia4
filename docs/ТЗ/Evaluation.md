# Evaluation (TBD – non-blocking)

Цель: измерение качества поведения и выхода моделей / RAG. Не блокирует текущую фазу.

## Метрики (черновик)

| Domain | Metric | Формула / Описание | Цель |
|--------|--------|--------------------|------|
| RAG | precision@k | релевантные / top_k | >0.7 |
| RAG | mrr | средняя 1/rank релевантного | ↑ |
| LLM | persona_adherence | процент ответов соответствующих persona rules | ↑ |
| LLM | hallucination_score | нормализованный показатель (eval набор) | ↓ |
| Memory | insight_novelty_mean | средний novelty_score | стабильность |
| UX | persona_drift_score | 1 - cosine(sim(embedding(answer), embedding(persona_canon))) усреднённое | ↓ |
| UX | empathy_mention_rate | эмпатические маркеры / N сообщений (N=20 окно) | ↑ |
| UX | intimacy_level_distribution | распределение состояний intimacy FSM (coverage) | целевой баланс |

Определения маркеров и FSM — отдельный раздел (позже). Источник данных: Message.Appended события + оффлайн judge.

## Pipelines

1. Offline batch (eval набор промптов → расчёт метрик).
2. Periodic (ночной) ре-оценка persona adherence.
3. On-demand A/B (две модели / две конфигурации).

## События (план)

| Event | Поля | Назначение |
|-------|------|------------|
| Eval.BatchStarted | batch_id, size | Запуск оценки |
| Eval.BatchFinished | batch_id, size, duration_ms | Конец |
| Eval.ModelJudged | request_id, judge_model_id, target_model_id, verdict | Результат сравнения |
