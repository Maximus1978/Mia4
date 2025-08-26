# Observability (TBD – non-blocking)

Цель: обеспечить прозрачность (Metrics + Structured Logging + Tracing) с минимальным вмешательством модулей.

## Компоненты

| Компонент | Назначение | Статус |
|-----------|------------|--------|
| MetricsExporter | Экспорт Prometheus (HTTP) | Planned |
| StructuredLogger | Форматирование JSON логов | Planned |
| TraceContext | Генерация correlation_id / span_id | Planned |
| EventIngestor | Подписка на EventBus → метрики | Planned |

## Метрики (начальный набор)

| Metric | Type | Labels | Источник |
|--------|------|--------|----------|
| generation_started_total | counter | model_id, role | GenerationStarted |
| generation_chunk_total | counter | model_id, role | GenerationChunk |
| generation_completed_total | counter | model_id, role, status | GenerationCompleted |
| generation_completed_errors_total | counter | model_id, role, error_type | GenerationCompleted(status=error) |
| model_loaded_total | counter | model_id, role | ModelLoaded |
| model_load_ms | histogram | model_id | ModelLoaded.load_ms |
| decode_tps | gauge | model_id, role | GenerationCompleted.result_summary.timings.decode_tps |

## Логирование

- Единый JSON формат: {ts, level, event?, msg, request_id?, correlation_id?}.
- Корреляция: request_id у Generation*; correlation_id прокидывается через EventBus (позже).

## Трассировка (упрощённо)

- В v1 только propagation `correlation_id` (UUID4) в контексте.
- В v2 (опционально) span boundary: generation, retrieval, memory_write.

## Конфигурация

Ключи зафиксированы в `Config-Registry.md` (canonical). Повтор здесь исключительно для обзорной читабельности:

| Key | Default | Назначение |
|-----|---------|-----------|
| observability.metrics.enabled | true | Включение экспорта |
| observability.metrics.port | 9090 | HTTP порт |
| observability.logging.level | info | Базовый уровень |
| observability.tracing.enabled | false | Включение trace контекста |

Canonical source: см. строкы observability.* в `Config-Registry.md`.

## События потребления

Подписка: все события для метрик; отфильтрованные ошибки для alert counters.
