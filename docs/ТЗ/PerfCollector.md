# PerfCollector (TBD – non-blocking)

Дополняет perf методологию: агрегирует события Generation* / ModelLoaded → сводные метрики и regression guard.

## Потоки данных

1. Подписка на EventBus (GenerationStarted / Finished / Failed / ModelLoaded).
2. Поддержание rolling window измерений (latency, tokens/sec).
3. Пороговая логика (thresholds из конфигурации) → события Performance.Degraded (план).

## Артефакты

| Артефакт | Формат | Назначение |
|----------|--------|------------|
| perf_baseline_snapshot.json | JSON | Эталонная база метрик |
| perf_probe.json | JSON | Текущий прогон для сравнения |

## Конфигурация (план)

| Key | Default | Описание |
|-----|---------|----------|
| perf.collector.enabled | true | Включение подсистемы |
| perf.collector.window | 50 | Кол-во последних генераций в окне |
| perf.collector.degradation_pct | 0.15 | Порог относительного падения tps |

## Расширения

- Histogram latency buckets (отложено).
- Async dispatch support (после EventBus v2).
