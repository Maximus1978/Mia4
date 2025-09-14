# Паспорт модели: phi-3.5-mini-instruct-q3_k_s

> Cross-links: [Общий реестр моделей](../Модели%20ИИ.md), [Config Registry](../Config-Registry.md), [README](../../README.md), [Инструкции](../../.instructions.md)

## 1. Идентификация

- id: `phi-3.5-mini-instruct-q3_k_s`
- family: `phi`
- role: `lightweight`
- quant: `Q3_K_S`
- file: `models/Phi-3.5-mini/Phi-3.5-mini-instruct_Uncensored-Q3_K_S.gguf`
- context_length: 8192
- revision: `r1`
- capabilities: chat (judge reuse для small tasks через alias)

## 2. Назначение

Быстрые ответы, smoke-тест потоковой инфраструктуры, fallback при недоступности primary.

## 3. Ключи конфигурации

| Ключ | Значение | Примечание |
|------|----------|-----------|
| llm.lightweight.id | phi-3.5-mini-instruct-q3_k_s | Выбор модели |
| llm.lightweight.temperature | 0.4 (план: 0.7–0.8 baseline) | Повысить для полноты |
| llm.heavy_model_vram_threshold_gb | 10.0 | Не heavy (не триггерит unload) |
| llm.postproc.* | (см. primary) | Общий постпроцессор |

## 4. Производительность (сводка)

| Метрика | Значение | Источник |
|---------|----------|----------|
| first_token_latency_ms (warm) | ~8–9 ms | perf smoke |
| decode_tps | ~143 | perf smoke |

## 5. Поведение reasoning

Обычно генерирует меньше reasoning; reasoning_max_tokens в пресетах ограничивает «болтовню». План: при high reasoning автоматически эскалировать на primary (policy rule TBD).

## 6. События

Использует ModelLoaded / ModelDowngraded (CPU fallback при низком VRAM <1GB) + Generation*.

## 7. Риски / ограничения

- Качество reasoning ниже primary → не использовать для сложного планирования.
- Возможное расхождение temperature между пресетами и базовым sampling (нормализовать).

## 8. План улучшений

1. Скорректировать temperature до 0.7–0.8 для баланса полноты.
2. Добавить правило auto-escalation: если prompt_complexity_score>threshold → перенаправить на primary.
3. Метрика escalations_total для мониторинга.
4. Поддержка adaptive max_output_tokens (меньше лимиты чем у primary).
5. Включить lightweight-only fast path (без ngram suppression?) опционально.

## 9. Связанные документы

- [Config Registry: llm.lightweight.*](../Config-Registry.md#config-registry)
- [Общий список моделей](../Модели%20ИИ.md)
- [Инструкции / План работ](../../.instructions.md)

## 10. Backlink Index

README, Config-Registry, Модели ИИ, Инструкции.

---
Последнее обновление: 2025-08-29.
