# Паспорт модели: gpt-oss-20b-mxfp4

> Cross-links: [Общий реестр моделей](../Модели%20ИИ.md), [Config Registry](../Config-Registry.md), [Perf](../Perf.md), [README](../../README.md), [Инструкции](../../.instructions.md)

## 1. Идентификация

- id: `gpt-oss-20b-mxfp4`
- family: `gpt-oss`
- role: `primary`
- quant: `MXFP4` (mixed FP4)
- file: `models/gpt-oss-20b-GGUF/gpt-oss-20b-MXFP4.gguf`
- context_length: 32768 (текущая конфигурация)
- revision: `r1`
- capabilities: chat, judge (alias), plan, long_context

## 2. Назначение

Primary baseline (качество + длинный контекст) для основных пользовательских ответов и планирующих шагов. Используется как источник финального ответа при разделении reasoning/final.

## 3. Ключи конфигурации

| Ключ | Значение (base.yaml) | Примечание |
|------|----------------------|-----------|
| llm.primary.id | gpt-oss-20b-mxfp4 | Выбор модели |
| llm.primary.temperature | 0.7 (план: 1.0) | Нормализация (research) |
| llm.primary.top_p | 0.9 (план: 1.0) | Увеличить для полноты |
| llm.primary.top_k | 40 (план: 0) | 0 → отключение top-k (llama.cpp behaviour) |
| llm.primary.repeat_penalty | 1.1 | Лёгкое сдерживание повторов |
| llm.primary.max_output_tokens | 1024 | План: адаптивный лимит |

## 4. Производительность (сводка)

| Метрика | Значение (последние наблюдения) | Источник |
|---------|---------------------------------|----------|
| first_token_latency_ms (warm) | ~26 ms | perf logs / events |
| decode_tps | 42–46 | `reports/perf_*` / events |
| reasoning_ratio (цель) | <0.35 (набл.) | GenerationCompleted.result_summary |

## 5. Поведение reasoning → final

Полностью Harmony: каналы `analysis` (stream, не сохраняется) и `final` (ответ). Если спец‑токены отсутствуют — всё считается `final`.

## 6. События и метрики

| Событие | Использование |
|---------|---------------|
| ModelLoaded | Успешная загрузка (metadata: free_vram_mb_before) |
| ModelUnloaded | При переключении heavy моделей |
| ModelAliasedLoaded | При создании alias (judge) |
| GenerationStarted/Completed | Основные метрики latency, decode_tps |
| ReasoningPresetApplied | Фиксация профиля reasoning |

Доп. метрики: `model_provider_reuse_total` (alias reuse), `reasoning_buffer_latency_ms`, план — `reasoning_ratio_alert_total`.

## 7. Известные риски / ограничения

- VRAM pressure при одновременной загрузке других heavy моделей → реализован авто-unload (ModuleManager) и downgrade для lightweight, но не для primary.
- Потенциальная усечённость ответа при слишком низких sampling параметрах (обнаружено снижение качества → план нормализации).

## 8. План улучшений (влияющих на модель)

1. Перейти на Harmony формат system/developer/user (замена/расширение system_prompt).
2. Нормализовать sampling: temperature=1.0, top_p=1.0, top_k=0 (сохранить repeat_penalty).
3. Adaptive max_output_tokens: heuristic по длине prompt и reasoning_ratio.
4. Stop sequence для финального маркера (на переходном этапе) → затем отказ от маркера.
5. Добавить метрику `reasoning_ratio_alert_total` (порог, напр. >0.45).
6. Ввести конфиг профилей Throughput vs Quality (переключение n_threads / n_batch).
7. Версионировать system prompt: hash + semantic version (already version=1; hash в событии). План v2 после Harmony.

## 9. Связанные документы

- [Config Registry: llm.primary.*](../Config-Registry.md#config-registry)
- [Общий список моделей](../Модели%20ИИ.md)
- [Perf характеристики](../Perf.md)
- [Инструкции / План работ](../../.instructions.md)

## 10. Backlink Index

Документы, содержащие ссылку на этот паспорт: README, Config-Registry, Модели ИИ, Perf, Инструкции.

---
Последнее обновление: 2025-08-29.
