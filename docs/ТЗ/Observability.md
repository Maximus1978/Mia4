# Observability (TBD – non-blocking)

Цель: обеспечить прозрачность (Metrics + Structured Logging + Tracing) с минимальным вмешательством модулей.

## Компоненты

| Компонент | Назначение | Статус |
|-----------|------------|--------|
| MetricsExporter | Экспорт Prometheus (HTTP) | Planned |
| StructuredLogger | Форматирование JSON логов | Planned |
| TraceContext | Генерация correlation_id / span_id | Planned |
| EventIngestor | Подписка на EventBus → метрики | Planned |

## Метрики (начальный набор + расширения 2025-08-26)

| Metric | Type | Labels | Источник |
|--------|------|--------|----------|
| generation_started_total | counter | model_id, role | GenerationStarted |
| generation_chunk_total | counter | model_id, role | GenerationChunk |
| generation_completed_total | counter | model_id, role, status | GenerationCompleted |
| generation_completed_errors_total | counter | model_id, role, error_type | GenerationCompleted(status=error) |
| model_loaded_total | counter | model_id, role | ModelLoaded |
| model_load_ms | histogram | model_id | ModelLoaded.load_ms |
| decode_tps | gauge | model_id, role | GenerationCompleted.result_summary.timings.decode_tps |
| env_override_total | counter | path | ConfigLoader (_apply_env) |
| config_validation_errors_total | counter | path, code | ConfigLoader (_normalize_and_validate) |

Описание добавленных (2025-08-26):

| Metric | Semantics |
|--------|-----------|
| env_override_total | Инкремент при успешной подстановке ENV (значение маскируется в логе) |
| config_validation_errors_total | Ошибка правил (диапазон/формат). code → `config-out-of-range` или `config-invalid` (ADR-0006) |

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

Canonical source: см. строки observability.* в `Config-Registry.md`.

## Config Validation & ENV Override Metrics (2025-08-26)

`env_override_total{path}` — аудит использования конфигурационных ENV (детект дрейф без diff файлов). Значение не логируется в открытом виде.

`config_validation_errors_total{path,code}` — нарушения правил (`top_p` вне (0,1], `max_output_tokens<=0`, и т.п.). `code` соответствует error taxonomy (`config-out-of-range`, `config-invalid`). Ошибка блокирует загрузку конфигурации.

Цель: раннее обнаружение конфигурационных дрейфов и количественный контроль диапазонов без выделенного observability модуля.

## События потребления

Подписка: все события для метрик; отфильтрованные ошибки для alert counters.
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
