# ADR-0009: Reflection & Insight Generation Cycle

Status: Accepted (2025-08-25)

## Контекст
Нужна периодическая «рефлексия» для генерации инсайтов и обновления предпочтений без вмешательства пользователя.

## Решение

Триггеры запуска:

1. Cron по `reflection.schedule.cron` (nightly 03:00).
2. On-demand если: `session_total_tokens > reflection.triggers.token_threshold (8000)` или idle времени сессии > `reflection.triggers.idle_seconds (7200)`.

Процесс:

```text
collect recent messages → cluster / summarize → extract themes (insights) → store insights.jsonl → emit Reflection.RunFinished.
```

Конфиг ключи (Accepted):

- `reflection.triggers.token_threshold` (int, default 8000)
- `reflection.triggers.idle_seconds` (int, default 7200)


## Варианты

1. Только nightly — медленная адаптация.
2. Каждое сообщение — высокие издержки.

## Обоснование
Гибрид снижает задержку обучения без перегрузки.

## Последствия
Нужен подсчёт токенов по сессии и учет времени последнего сообщения.

## Безопасность / Наблюдаемость
Инсайты не должны содержать PII в открытом виде — возможна псевдонимизация.

## Связанные документы

- UX поведение Мии

## Примечания
Оценка качества инсайтов будет добавлена позже (evaluation pipeline).
