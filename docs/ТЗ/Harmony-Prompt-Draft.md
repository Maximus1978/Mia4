# Harmony Prompt Draft (v2 System Layer Plan)

Цель: заменить маркер `===FINAL===` на структурированные каналы (analysis / final) через многоуровневый промпт и последующую SSE сегрегацию.

## 1. Слои

1. system (инвариантные правила + безопасность + стиль)
2. developer (временные инструкции / экспериментальные ограничения)
3. user (фактический запрос)

## 2. Формат system слоя (предварительно)

```text
[SYSTEM v2]
Role: Mia (concise, factual, Russian primary, English technical terms allowed).
You produce two phases:
<analysis> internal structured reasoning in Russian (concise bullet thoughts, no final answer, no self-reference).
<final> user-facing answer (clean, no meta commentary, no analysis leakage).
Rules:
1. Never include <analysis> content in <final>.
2. If insufficient info, say "не знаю".
3. Respect persona & tools output that may follow.
Output format:
<analysis>
...reasoning...
</analysis>
<final>
...answer...
</final>
```

## 3. Миграция

| Этап | Действие | Риск |
|------|----------|------|
| 1 | Внедрить draft system_prompt v2 (behind feature flag) | Drift в стиле |
| 2 | Постпроцессор: распознавание тегов `<analysis>`/`<final>` | Некорректный парс при вложенных тегах |
| 3 | SSE: заменить reasoning/event на channel=analysis/final | UI адаптация |
| 4 | Удалить маркер (выполнено) | Совместимость старых тестов |

## 4. Тесты

- split tags success
- fallback: если нет тегов → всё final
- no leakage: проверка отсутствия analysis текста в final

## 5. Конфиг ключи (план)

- llm.prompt.harmony.enabled (bool)
- llm.prompt.harmony.tags.analysis = "analysis"
- llm.prompt.harmony.tags.final = "final"

## 6. Метрики

- analysis_tokens, final_tokens (reuse existing fields)
- harmony_tag_mismatch_total

## 7. Следующие шаги

1. Добавить feature flag в конфиг.
2. Расширить postproc для тегов.
3. Изменить system_prompt version=2 (draft) условно.

---
Draft 2025-08-29.
