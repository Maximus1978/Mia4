# ADR-0001: GenerationResult V2

Status: Proposed

## Контекст

Текущая версия (v1) содержит поля: text, usage{prompt_tokens, completion_tokens}, timings{total_ms, decode_tps}. Требуется стандартизовать версионирование и статус выполнения для унификации downstream (perf, observability) и расширения обработки ошибок.

## Решение (Предложение)

Ввести структуру v2:

```json
{
  "version": 2,
  "status": "success" | "error",
  "text": "...",
  "usage": {"prompt_tokens": int, "completion_tokens": int},
  "timings": {"total_ms": int, "decode_tps": float},
  "error": {"type": str, "message": str}?  # присутствует если status=error
}
```

## Варианты

1. Добавить только поле version (минимум) — недостаточно семантики успех/ошибка.
2. Использовать исключения вместо status=error — усложняет унифицированный контракт событий.

## Обоснование

- Явный status упрощает метрики (counter success/failed) без try/except вокруг вызовов.
- Версия позволяет безопасно эволюционировать контракт без ломки потребителей.

## Последствия

### Положительные

- Прозрачная эволюция, наблюдаемость улучшена, унификация PerfCollector.

### Отрицательные

- Необходимость миграции тестов и адаптеров провайдеров.

## Безопасность / Наблюдаемость

- Ошибки стандартизованы → легче фильтровать чувствительные части текста при логировании.

## Связанные документы

- Events.md (GenerationFinished/Failed объединение в будущем? TBD)
- Config-Registry.md (threshold привязки к timings.decode_tps)
