# ADR-0011: EventBus Architecture (v1/v2)

Status: Accepted (2025-08-25)

## Контекст

Событийная модель фиксирована (ADR-0003, Events.md), но отсутствует формализация шины доставки. Нужно гарантировать: отделение эмиттера от потребителя, непрерывность при сбоях обработчиков, наблюдаемость.

## Требования v1

| Aspect | Требование |
|--------|------------|
| Модель | In-process, sync |
| API | subscribe(event_name, handler), emit(event_name, payload) |
| Payload | dict со стандартной базой (ADR-0003) |
| Ordering | Для одного emit — последовательный вызов подписчиков; между разными событиями порядок не гарантируется |
| Ошибки обработчиков | Логируются, не прерывают остальных |
| Производительность | O(n_subscribers(event)) вызовы без очереди |
| Метрики | counter events_emitted_total{event}, handler_errors_total{event} |

## Эволюция v2 (план)

| Feature | Описание |
|---------|----------|
| Async очередь | Буфер (ring) размера N (config `events.queue.size`) |
| Backpressure | Drop oldest или блокировка по режиму (config) |
| Retry | Повтор обработчика с экспон. задержкой (limited) |
| Replay window | Keep last M events для late subscribers |
| Filtering | Подписка по префиксу (Session.*, Generation*) |

## Интерфейсы (псевдо)

```python
class EventBus:
    def subscribe(self, event: str, handler: Callable[[dict], None]): ...
    def emit(self, event: str, payload: dict): ...  # adds ts, validates base
```

## Валидация

- При emit добавляется `ts` если отсутствует.
- Поле `event` сверяется с Events.md (желательно предзагруженный set).
- (Future) schema_version в payload `v`.

## Логи

StructuredLogger пишет: {level=debug,event="_dispatch",target=...,handlers=K}

## Миграция v2

Адаптер поверх v1 API → drop-in; модули не меняют контракт.

## Последствия

Упрощает внедрение модулей (perf, observability) без циклических импортов.

## Связанные

- ADR-0003 (Payload Base)
- Events.md (перечень событий)
- ADR-0012 (GenerationResult Contract) для статуса generation.*
