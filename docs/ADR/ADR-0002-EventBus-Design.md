# ADR-0002: EventBus Design

Status: Proposed

## Контекст

Нужен унифицированный слой публикации внутренних событий: ModelLoaded, Generation*, RAG.* и т.д. Сейчас события описаны, но отсутствует формальная реализация Bus с версионированием payload.

## Решение (Предложение)

Ввести EventBus v1 (sync, in-process):

```python
class EventBus:
    def subscribe(self, event_name: str, handler: Callable[[dict], None]) -> None: ...
    def emit(self, event_name: str, payload: dict) -> None: ...
```

Правила:

1. Payload обязан иметь поле `event` (дублирует имя) и `ts` (float epoch).
2. Версии событий фиксируются в Events.md (таблица): если меняется структура → новое имя или поле `v`.
3. Handlers не должны бросать исключения наружу (wrap & log).

## Варианты

1. Async очередь сразу (сложнее тесты, повышает латентность разработки).
2. Сигналы через pydantic-модели (строже, но повышает связность). Отложено.

## Обоснование

- Простота внедрения, минимальные риски.
- Достаточно для PerfCollector и Observability MVP.

## Последствия

### Положительные

- Единая точка расширения (позже: async, буфер, фильтры).

### Отрицательные

- Потенциальная блокировка если handler медленный (будет решено в v2 async).

## Безопасность / Наблюдаемость

- Centralized logging точка — можно внедрить correlation_id прокидку.

## Связанные документы

- Events.md
- ARCHITECTURE_GUARDS.md
