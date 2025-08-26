# ADR-0007: Streaming Contract & Context Budget

Status: Accepted (2025-08-25)

## Контекст
Нужно стандартизовать SSE поток генерации и алгоритм отбора сообщений (context budget) перед UX/UI фазой.

## Решение

SSE события (`event:` / `data:` строки):

1. `generation.token` – incremental: `{"seq":int,"token":"...","usage":{"completion_tokens":int}}`
2. `generation.progress` – периодически: `{"seq":int,"elapsed_ms":int}`
3. `generation.complete` – финал: сериализованный GenerationResult v2.
4. `generation.error` – при сбое: `{ "error": {"type": str, "message": str}, "correlation_id": "..." }`.

Context Budget алгоритм:

```text
1. Резервировать budget_total_tokens * prompt.context.fraction (0.30) под историю.
2. Включить минимум prompt.context.min_last_messages (6) последних сообщений.
3. Затем добавлять предыдущие сообщения назад пока не превышен budget_history.
4. Отдельно RAG вставки учитываются вне истории (отдельный slice бюджета).
```

Конфиг ключи (Accepted):

- `prompt.context.min_last_messages` (int, default 6)
- `prompt.context.fraction` (float, default 0.30)


## Варианты

1. Фиксированное N сообщений — хуже масштабируется по размеру окна.
2. Роlling summary — отложено до стабильной модели.

## Обоснование
Фракционная модель адаптируется к различным max context.

## Последствия
Нужны функции подсчёта токенов перед генерацией и fallback при превышении.

## Безопасность / Наблюдаемость
Token budget логировать (debug) для анализа дрейфа стоимости.

## Связанные документы

- UX поведение Мии
- ADR-0001 GenerationResult V2

## Примечания
Binary streaming (websocket) возможен позже; контракт совместим.
